"""Telemetria operacional com falhas rastreáveis e mensagens sanitizadas."""

import json
from types import SimpleNamespace

import pytest

from credito_monitorado import telemetry
from credito_monitorado.telemetry import Telemetry


def test_estagio_bem_sucedido_persiste_evento(tmp_path):
    telemetria = Telemetry(tmp_path)
    with telemetria.stage("validacao", rows=12):
        pass
    assert len(telemetria.events) == 1
    evento = telemetria.events[0]
    assert evento["stage"] == "validacao"
    assert evento["rows"] == 12
    assert not evento.get("error_type")
    linhas = (tmp_path / "logs.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(linhas[-1]) == evento


def test_estagio_falho_relanca_excecao_sem_expor_mensagem(tmp_path):
    telemetria = Telemetry(tmp_path)
    segredo = "CLIENTE_987654321_VALOR_CONFIDENCIAL"
    with pytest.raises(RuntimeError, match=segredo), telemetria.stage("treino", rows=4):
        raise RuntimeError(segredo)
    assert telemetria.events[-1]["stage"] == "treino"
    assert telemetria.events[-1]["error_type"] == "RuntimeError"
    conteudo = (tmp_path / "logs.jsonl").read_text(encoding="utf-8")
    assert segredo not in conteudo
    assert segredo not in json.dumps(telemetria.events)


def test_alerta_preserva_metadados_operacionais(tmp_path):
    telemetria = Telemetry(tmp_path)
    telemetria.alert(
        code="QUEDA_AUC",
        severity="high",
        scenario="mudanca_conceito",
        message="Queda de desempenho superior ao limiar configurado.",
    )
    assert len(telemetria.alerts) == 1
    alerta = telemetria.alerts[0]
    assert alerta["code"] == "QUEDA_AUC"
    assert alerta["severity"] == "high"
    assert alerta["scenario"] == "mudanca_conceito"
    assert alerta["message"] == "Queda de desempenho superior ao limiar configurado."


def test_recursos_sao_medidos_em_unidades_documentadas(tmp_path):
    recursos = Telemetry(tmp_path).snapshot_resources()
    assert recursos["rss_mb"] > 0
    assert recursos["cpu_seconds"] >= 0
    assert recursos["disk_free_gb"] >= 0


def test_interrupcao_registra_falha_e_relanca_sem_mensagem(tmp_path):
    telemetria = Telemetry(tmp_path)
    segredo = "INTERRUPCAO_COM_DADO_CONFIDENCIAL"
    with pytest.raises(KeyboardInterrupt), telemetria.stage("processamento"):
        raise KeyboardInterrupt(segredo)
    evento = telemetria.events[-1]
    assert evento["status"] == "falha"
    assert evento["error_type"] == "KeyboardInterrupt"
    assert segredo not in (tmp_path / "logs.jsonl").read_text(encoding="utf-8")


def test_disco_medido_no_diretorio_de_saida(tmp_path, monkeypatch):
    consultados = []

    def medir_disco(caminho):
        consultados.append(caminho)
        return SimpleNamespace(free=2 * 1024**3)

    monkeypatch.setattr(telemetry.psutil, "disk_usage", medir_disco)
    assert Telemetry(tmp_path).snapshot_resources()["disk_free_gb"] == pytest.approx(2.0)
    assert len(consultados) == 1
    assert str(consultados[0]) == str(tmp_path.resolve())


def test_alertas_saude_publicam_valor_observado_e_limiar(tmp_path):
    telemetria = Telemetry(tmp_path)
    telemetria.events = [{"stage": "treino", "duration_seconds": 12.0}]
    telemetria.resources = [{"rss_mb": 256.0, "disk_free_gb": 0.5}]
    telemetria.check_health(max_stage_seconds=10, max_rss_mb=128)
    alertas = {alerta["code"]: alerta for alerta in telemetria.alerts}
    assert set(alertas) == {"LATENCIA", "MEMORIA", "DISCO"}
    for codigo, observado, limiar in [
        ("LATENCIA", 12, 10),
        ("MEMORIA", 256, 128),
        ("DISCO", 0.5, 1),
    ]:
        assert alertas[codigo]["observed"] == pytest.approx(observado)
        assert alertas[codigo]["threshold"] == pytest.approx(limiar)
