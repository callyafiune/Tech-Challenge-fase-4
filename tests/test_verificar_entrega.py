"""Evidência da entrega exige correspondência dos bytes e caminhos confinados."""

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

_spec = importlib.util.spec_from_file_location(
    "verificar_entrega", Path(__file__).resolve().parents[1] / "scripts/verificar_entrega.py"
)
verificador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verificador)


def _hash(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


@pytest.fixture
def execucao(tmp_path):
    raiz = tmp_path
    config = {"seed": 42}
    (raiz / "params.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    fonte = {
        "files_sha256": {"src/modulo.py": "hash-da-fonte"},
        "source_sha256": "hash-global",
        "git_dirty": True,
    }
    diretorio = raiz / "artifacts/execucao-teste"
    diretorio.mkdir(parents=True)
    resumo = {
        "execution_id": diretorio.name,
        "status": "sucesso",
        "source": fonte,
        "config": config,
        "config_sha256": _hash(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()),
        "scenarios": {},
    }
    caminho = diretorio / "resumo.json"
    caminho.write_text(json.dumps(resumo), encoding="utf-8")
    (diretorio / "index.html").write_text("<html>Relatório válido</html>", encoding="utf-8")
    manifesto = {
        chave: resumo[chave]
        for chave in ["execution_id", "status", "source", "config_sha256", "scenarios"]
    }
    manifesto["artifacts_sha256"] = {
        arquivo.name: _hash(arquivo.read_bytes()) for arquivo in diretorio.iterdir()
    }
    (diretorio / "manifesto.json").write_text(json.dumps(manifesto), encoding="utf-8")
    return caminho, raiz, fonte


def test_mesmos_bytes_sao_aceitos_quando_apenas_git_dirty_muda(execucao):
    caminho, raiz, fonte = execucao
    resultado = verificador.validate_execution(caminho, raiz, {**fonte, "git_dirty": False})
    assert resultado["source_matches"]
    assert resultado["current_source_sha256"] == fonte["source_sha256"]


def test_registro_preserva_saida_literal_sem_inventar_captura_da_cli(execucao, monkeypatch):
    caminho, raiz, fonte = execucao
    documentos = raiz / "docs"
    documentos.mkdir()
    mlflow = documentos / "evidencias_mlflow.json"
    mlflow.write_text('{"runs": 5}', encoding="utf-8")
    monkeypatch.setattr(verificador, "__file__", str(raiz / "scripts/verificar_entrega.py"))
    monkeypatch.setattr(verificador, "_source_identity", lambda: {**fonte, "git_dirty": False})
    monkeypatch.setattr(sys, "argv", ["verificar_entrega.py", "--resumo", str(caminho)])
    resumo = json.loads(caminho.read_text(encoding="utf-8"))
    resumo.update(started_at_utc="2026-11-16T00:00:00Z", duration_seconds=1.0, alerts=[])
    caminho.write_text(json.dumps(resumo), encoding="utf-8")
    manifesto_path = caminho.with_name("manifesto.json")
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    manifesto["artifacts_sha256"]["resumo.json"] = _hash(caminho.read_bytes())
    manifesto_path.write_text(json.dumps(manifesto), encoding="utf-8")

    def executar_sem_processo(comando, **kwargs):
        if "pytest" in comando:
            (documentos / "validacao/pytest.xml").write_bytes(b"<testsuite tests='20'/>")
        return SimpleNamespace(
            stdout=b"saida literal\n", stderr=b"diagnostico literal\n", returncode=0
        )

    monkeypatch.setattr(verificador.subprocess, "run", executar_sem_processo)
    with pytest.raises(SystemExit) as termino:
        verificador.main()
    assert termino.value.code == 0
    registro = json.loads((documentos / "verificacao.json").read_text(encoding="utf-8"))
    assert registro["source_matches"]
    assert registro["execucao_real"]["command_reference"] == "não capturado da CLI original"
    assert registro["execucao_real"]["cli_exit_code"] == "não capturado da CLI original"
    assert registro["execucao_real"]["status"] == "sucesso"
    for comando in registro["comandos"]:
        assert comando["saida_literal"] == "saida literal\ndiagnostico literal\n"
        assert comando["sha256"] == _hash((raiz / comando["arquivo"]).read_bytes())
    assert registro["evidencias_adicionais_sha256"]["docs/evidencias_mlflow.json"] == _hash(
        mlflow.read_bytes()
    )
    assert registro["evidencias_adicionais_sha256"]["docs/validacao/pytest.xml"] == _hash(
        (documentos / "validacao/pytest.xml").read_bytes()
    )


@pytest.mark.parametrize(
    "alteracao",
    [
        "fonte",
        "hash_fonte",
        "config",
        "resumo",
        "artefato",
        "fora_manifesto",
        "manifesto",
    ],
)
def test_entrega_rejeita_inconsistencia_ou_adulteracao(execucao, alteracao):
    caminho, raiz, fonte = execucao
    resumo = json.loads(caminho.read_text(encoding="utf-8"))
    if alteracao == "fonte":
        fonte = {**fonte, "files_sha256": {"src/modulo.py": "fonte-alterada"}}
    elif alteracao == "hash_fonte":
        fonte = {**fonte, "source_sha256": "hash-global-alterado"}
    elif alteracao == "config":
        (raiz / "params.yaml").write_text("seed: 99\n", encoding="utf-8")
    elif alteracao == "resumo":
        resumo["campo_adulterado"] = "alterado"
        caminho.write_text(json.dumps(resumo), encoding="utf-8")
    elif alteracao == "artefato":
        (caminho.parent / "index.html").write_text("HTML adulterado", encoding="utf-8")
    elif alteracao == "fora_manifesto":
        (caminho.parent / "arquivo_extra.json").write_text("{}", encoding="utf-8")
    else:
        manifesto_path = caminho.with_name("manifesto.json")
        manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
        manifesto["execution_id"] = "outra-execucao"
        manifesto_path.write_text(json.dumps(manifesto), encoding="utf-8")
    with pytest.raises(ValueError):
        verificador.validate_execution(caminho, raiz, fonte)


def test_id_do_diretorio_deve_corresponder_a_execucao_integra(execucao):
    caminho, raiz, fonte = execucao
    copia = caminho.parent.with_name("outro-id")
    shutil.copytree(caminho.parent, copia)
    with pytest.raises(ValueError, match="identidade"):
        verificador.validate_execution(copia / "resumo.json", raiz, fonte)


def test_execucao_com_falha_coerente_e_hashes_validos_nao_comprova_sucesso(execucao):
    caminho, raiz, fonte = execucao
    resumo = json.loads(caminho.read_text(encoding="utf-8"))
    resumo["status"] = "falha"
    caminho.write_text(json.dumps(resumo), encoding="utf-8")
    manifesto_path = caminho.with_name("manifesto.json")
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    manifesto["status"] = "falha"
    manifesto["artifacts_sha256"]["resumo.json"] = _hash(caminho.read_bytes())
    manifesto_path.write_text(json.dumps(manifesto), encoding="utf-8")
    with pytest.raises(ValueError, match="sucesso"):
        verificador.validate_execution(caminho, raiz, fonte)


def test_caminho_externo_e_rejeitado_antes_de_ler_seus_bytes(execucao, monkeypatch):
    caminho, raiz, fonte = execucao
    externo = raiz / "externo.txt"
    externo.write_bytes(b"fora da execucao")
    manifesto_path = caminho.with_name("manifesto.json")
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    manifesto["artifacts_sha256"]["../../externo.txt"] = _hash(externo.read_bytes())
    manifesto_path.write_text(json.dumps(manifesto), encoding="utf-8")
    ler_bytes = Path.read_bytes

    def leitura_confinada(arquivo):
        if arquivo.resolve() == externo.resolve():
            raise AssertionError("Arquivo externo não pode ser lido pelo verificador.")
        return ler_bytes(arquivo)

    monkeypatch.setattr(Path, "read_bytes", leitura_confinada)
    with pytest.raises(ValueError, match="fora da execução"):
        verificador.validate_execution(caminho, raiz, fonte)
