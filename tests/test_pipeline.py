"""Bloqueios operacionais persistem evidência segura antes de interromper o fluxo."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml
from test_drift import criar_base

from credito_monitorado import pipeline, reporting
from credito_monitorado.data import split_dataset
from credito_monitorado.telemetry import Telemetry


def test_falha_aquisicao_persiste_resumo_seguro_e_relanca(tmp_path, monkeypatch):
    segredo = "IDENTIFICADOR_CONFIDENCIAL_987654321"

    def aquisicao_indisponivel(*args, **kwargs):
        raise RuntimeError(segredo)

    monkeypatch.setattr(pipeline, "acquire_dataset", aquisicao_indisponivel)
    configuracao = Path(__file__).resolve().parents[1] / "params.yaml"
    destino = tmp_path / "execucoes"
    with pytest.raises(RuntimeError, match=segredo):
        pipeline.run_pipeline(
            configuracao,
            destino,
            data_dir=tmp_path / "dados",
            tracking_uri=f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}",
        )
    caminhos = list(destino.glob("*/resumo.json"))
    assert len(caminhos) == 1
    resumo = json.loads(caminhos[0].read_text(encoding="utf-8"))
    assert resumo["status"] == "falha"
    assert resumo["failure"]["error_type"] == "RuntimeError"
    assert resumo["tracking"]["status"] != "completed"
    for caminho in caminhos[0].parent.glob("*.json*"):
        assert segredo not in caminho.read_text(encoding="utf-8")


def test_demonstracao_bloqueia_lotes_invalidos_antes_da_inferencia(tmp_path, monkeypatch):
    def inferencia_proibida(*args, **kwargs):
        raise AssertionError("Lote inválido não deve alcançar a inferência.")

    monkeypatch.setattr(pipeline, "predict", inferencia_proibida)
    telemetria = Telemetry(tmp_path)
    resultado = pipeline._contract_demo(criar_base(200), telemetria)
    assert resultado["status"] == "blocked_as_expected"
    assert resultado["inference_calls"] == 0
    assert resultado["rows_received"] == resultado["rejected_rows"] == 10
    assert {regra["rule"] for regra in resultado["rules"]} == {
        "nulo",
        "idade",
        "duplicidade",
        "combinado",
    }
    assert all(regra["blocked"] for regra in resultado["rules"])
    assert resultado["positive_control_validated"]
    assert telemetria.events[0]["stage"] == "contrato_controle_positivo"
    assert sum(evento["status"] == "sucesso" for evento in telemetria.events) == 1
    assert sum(evento["status"] == "falha" for evento in telemetria.events) == 4


@pytest.mark.parametrize("problema", ["sobreposicao", "cobertura"])
def test_verificacao_particoes_bloqueia_sobreposicao_e_perda_de_registros(problema):
    base = criar_base(200)
    partes = split_dataset(base)
    pipeline._verify_partitions(partes, base)
    if problema == "sobreposicao":
        partes["validation"].loc[0, "record_id"] = partes["train"].loc[0, "record_id"]
    else:
        partes["validation"] = partes["validation"].iloc[1:]
    with pytest.raises(RuntimeError):
        pipeline._verify_partitions(partes, base)


@pytest.mark.parametrize("esquema", ["http", "https", "postgresql", "mysql", "sqlite"])
def test_uri_tracking_nao_publica_credenciais_nem_query(esquema):
    if esquema == "sqlite":
        uri = "sqlite:///banco.db?token=SEGREDO_QUERY#SEGREDO_FRAGMENTO"
    else:
        uri = f"{esquema}://USUARIO_PRIVADO:SENHA_PRIVADA@host/banco?token=SEGREDO_QUERY#SEGREDO_FRAGMENTO"
    segura = pipeline._safe_tracking_uri(uri)
    partes = urlsplit(segura)
    assert partes.username is None
    assert partes.password is None
    assert not partes.query
    assert not partes.fragment
    for segredo in ["USUARIO_PRIVADO", "SENHA_PRIVADA", "SEGREDO_QUERY", "SEGREDO_FRAGMENTO"]:
        assert segredo not in segura
    assert segura == ("sqlite:///banco.db" if esquema == "sqlite" else "destino_remoto_omitido")


@pytest.mark.parametrize(
    "uri",
    [
        "postgresql://usuario:pa/ss@host/banco?token=segredo",
        "postgresql://usuario:12/ss@host/db",
        "postgresql://usuario:/ss@host/db",
        "mysql://usuario:8080?x@host/db",
        "https://[endereco-invalido",
    ],
)
def test_uri_malformada_nao_publica_senha_com_barra(uri):
    assert pipeline._safe_tracking_uri(uri) == "destino_remoto_omitido"


def test_arroba_no_caminho_remoto_nao_publica_trecho_do_caminho_como_host():
    assert (
        pipeline._safe_tracking_uri("https://host/pasta@SEGREDO_CAMINHO")
        == "destino_remoto_omitido"
    )


def test_relatorio_apresenta_rotulos_originais_como_observados(tmp_path):
    resumo = {
        "execution_id": "teste",
        "started_at_utc": "2026-11-16T00:00:00Z",
        "scenarios": {
            "control": {
                "rows": 200,
                "labels_status": "original_labels",
                "evidently_html": "evidently.html",
                "drift": {"summary": {"drifted_features": []}, "features": {}},
            }
        },
    }
    html = reporting.render_summary(resumo, tmp_path).read_text(encoding="utf-8")
    assert "<td>observados</td>" in html
    assert "original_labels" not in html


def test_falha_fora_de_estagio_nao_e_atribuida_a_bloqueio_esperado(tmp_path, monkeypatch):
    origem = tmp_path / "dados"
    origem.mkdir()
    xls = origem / "sintetico.xls"
    xls.write_bytes(b"fixture sintetica")
    (origem / "manifest.json").write_text(json.dumps({"synthetic": True}), encoding="utf-8")
    monkeypatch.setattr(pipeline, "acquire_dataset", lambda caminho: xls)
    monkeypatch.setattr(pipeline, "load_dataset", lambda *args, **kwargs: criar_base(5000))

    def falhar_apos_bloqueio_esperado(frame, telemetria):
        try:
            with telemetria.stage("bloqueio_esperado", expected_failure=True):
                raise ValueError("Violação de contrato esperada.")
        except ValueError:
            pass
        raise RuntimeError("Falha operacional fora de estágio.")

    monkeypatch.setattr(pipeline, "_contract_demo", falhar_apos_bloqueio_esperado)
    config = Path(__file__).resolve().parents[1] / "params.yaml"
    with pytest.raises(RuntimeError, match="fora de estágio"):
        pipeline.run_pipeline(
            config,
            tmp_path / "execucoes",
            data_dir=origem,
            tracking_uri=f"sqlite:///{(tmp_path / 'tracking.db').as_posix()}",
        )
    resumo = next((tmp_path / "execucoes").glob("*/resumo.json"))
    assert json.loads(resumo.read_text(encoding="utf-8"))["failure"]["failed_stage"] == "pipeline"


@pytest.mark.integracao
@pytest.mark.parametrize("backend", ["falha", "sqlite"])
def test_pipeline_real_consolida_artefatos_e_estado_do_tracking(tmp_path, monkeypatch, backend):
    """Substitui somente a origem; SQLite e todos os cálculos permanecem reais."""
    configuracao = Path(__file__).resolve().parents[1] / "params.yaml"
    config = yaml.safe_load(configuracao.read_text(encoding="utf-8"))
    config["simulation"]["batch_size"] = 200
    config["model"]["max_iter"] = 10
    caminho_config = tmp_path / "params.yaml"
    caminho_config.write_text(yaml.safe_dump(config), encoding="utf-8")
    origem = tmp_path / "dados"
    origem.mkdir()
    xls = origem / "sintetico.xls"
    xls.write_bytes(b"fixture sintetica, sem dados de clientes")
    (origem / "manifest.json").write_text(
        json.dumps({"source_rows": 5000, "synthetic": True}), encoding="utf-8"
    )
    monkeypatch.setattr(pipeline, "acquire_dataset", lambda caminho: xls)
    monkeypatch.setattr(pipeline, "load_dataset", lambda caminho, **kwargs: criar_base(5000))

    def tracking_indisponivel(*args, **kwargs):
        raise RuntimeError("SEGREDO_TRACKING_NAO_PUBLICAR")

    if backend == "falha":
        monkeypatch.setattr(pipeline, "track_execution", tracking_indisponivel)
    destino = tmp_path / "execucoes"
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    if backend == "falha":
        with pytest.raises(RuntimeError, match="SEGREDO_TRACKING"):
            pipeline.run_pipeline(caminho_config, destino, data_dir=origem, tracking_uri=uri)
    else:
        retornado = pipeline.run_pipeline(
            caminho_config,
            destino,
            data_dir=origem,
            tracking_uri=uri,
        )
    caminhos = list(destino.glob("*/resumo.json"))
    assert len(caminhos) == 1
    resumo = json.loads(caminhos[0].read_text(encoding="utf-8"))
    if backend == "falha":
        assert resumo["status"] == "falha"
        assert resumo["tracking"]["status"] == "failed"
    else:
        assert resumo["status"] == retornado["status"] == "sucesso"
        assert resumo["tracking"]["status"] == "completed"
    assert resumo["contracts"]["status"] == "blocked_as_expected"
    assert set(resumo["scenarios"]) == {"control", "covariate", "concept", "combined"}
    assert resumo["model"]["roundtrip_predictions_equal"]
    assert resumo["model"]["reference_metrics"]["roc_auc"] > 0.95
    assert resumo["fairness"]["groups"]
    assert "SEGREDO_TRACKING" not in caminhos[0].read_text(encoding="utf-8")
    html = (caminhos[0].parent / "index.html").read_text(encoding="utf-8")
    assert "Referência independente" in html
    assert "Auditoria descritiva de grupos" in html
    assert "Combinado comparado ao covariável" in html
    _verificar_links_locais(html, caminhos[0].parent)
    if backend == "sqlite":
        from mlflow.tracking import MlflowClient

        cliente = MlflowClient(tracking_uri=uri)
        pai = cliente.get_run(resumo["tracking"]["run_id"])
        assert pai.info.status == "FINISHED"
        assert pai.data.metrics["referencia_roc_auc"] > 0.95
        assert pai.data.params["modelo_max_iter"] == "10"
        filhos = cliente.search_runs(
            [pai.info.experiment_id],
            filter_string=f"tags.mlflow.parentRunId = '{pai.info.run_id}'",
        )
        assert len(filhos) == 4
        assert {filho.data.tags["mlflow.runName"] for filho in filhos} == set(resumo["scenarios"])
        assert all(filho.info.status == "FINISHED" for filho in filhos)
        for filho in filhos:
            assert filho.data.tags["relatorio_run_pai"] == pai.info.run_id
            arquivos = cliente.list_artifacts(filho.info.run_id)
            assert "estatisticas.json" in {arquivo.path for arquivo in arquivos}
            assert not any(arquivo.path.endswith(".html") for arquivo in arquivos)
        historia = cliente.get_metric_history(pai.info.run_id, "janela_roc_auc")
        assert sorted(ponto.step for ponto in historia) == [0, 1, 2, 3]
        download = tmp_path / "download"
        download.mkdir()
        artefatos = Path(
            cliente.download_artifacts(pai.info.run_id, "observabilidade", str(download))
        )
        html_mlflow = (artefatos / "index.html").read_text(encoding="utf-8")
        _verificar_links_locais(html_mlflow, artefatos)
        registrado = json.loads((artefatos / "resumo.json").read_text(encoding="utf-8"))
        assert registrado["status"] == "sucesso"
        assert registrado["events"] == resumo["events"]
        assert (artefatos / "auditoria_grupos.json").is_file()


def _verificar_links_locais(html, diretorio):
    """Links relativos do relatório devem resolver no disco e no artefato baixado."""
    links = re.findall(r"href=[\"\']([^\"\']+)[\"\']", html)
    relativos = [link for link in links if not urlsplit(link).scheme and not link.startswith("#")]
    assert relativos
    for link in relativos:
        assert (diretorio / urlsplit(link).path).is_file(), link
