"""Protege caminhos privados nas cópias destinadas à publicação."""

import json
from pathlib import Path, PurePosixPath

from credito_monitorado.publicacao import salvar_saida_publica, sanitizar_caminhos


def test_remove_raiz_e_usuario_inclusive_em_json_sem_alterar_urls(tmp_path):
    raiz = tmp_path / "projeto"
    usuario = tmp_path / "usuario"
    texto = json.dumps(
        [str(raiz / "pyproject.toml"), str(usuario / ".config"), "https://exemplo.org/x"],
        ensure_ascii=False,
    )
    saida = sanitizar_caminhos(texto, raiz, usuario)
    assert json.loads(saida) == ["./pyproject.toml", "[USUARIO]/.config", "https://exemplo.org/x"]


def test_saida_publica_preserva_original_apenas_em_artifacts(tmp_path):
    destino = tmp_path / "docs/validacao/comando.log"
    original = f"Relatório: {tmp_path / 'artifacts/index.html'}\r\n".encode()
    publicado = salvar_saida_publica(original, destino, tmp_path)
    assert publicado == ("Relatório: ./" + str(Path("artifacts/index.html")) + "\r\n").encode()
    assert destino.read_bytes() == publicado
    privados = list((tmp_path / "artifacts/evidencias_privadas").rglob("*.log"))
    assert len(privados) == 1
    assert privados[0].read_bytes() == original


def test_caminhos_windows_escapados_e_prefixos_parecidos():
    texto = r"C:\\projeto\\docs\\x.json C:\projeto-extra\x https://exemplo.org"
    assert sanitizar_caminhos(texto, Path("C:/projeto"), Path("C:/Users/teste")) == (
        r"./docs\\x.json C:\projeto-extra\x https://exemplo.org"
    )


def test_json_preserva_escapes_apos_caminho_exato(tmp_path):
    texto = json.dumps(
        {"saida": f"{tmp_path}\nconfiguração", "aninhado": json.dumps(str(tmp_path))}
    )
    destino = tmp_path / "docs/resumo.json"
    saida = salvar_saida_publica(texto.encode(), destino, tmp_path)
    dados = json.loads(saida)
    assert dados["saida"] == ".\nconfiguração"
    assert json.loads(dados["aninhado"]) == "."


def test_preserva_bytes_nao_utf8_e_remove_nome_da_maquina_no_xml(tmp_path):
    log = tmp_path / "docs/saida.log"
    assert salvar_saida_publica(b"falha: \xe7\n", log, tmp_path) == b"falha: \xe7\n"
    xml = b'<testsuite hostname="maquina-privada"/>'
    assert salvar_saida_publica(xml, tmp_path / "docs/pytest.xml", tmp_path) == (
        b'<testsuite hostname="[MAQUINA]"/>'
    )


def test_jsonl_mantem_um_registro_por_linha(tmp_path):
    linha = json.dumps({"caminho": str(tmp_path / "arquivo")})
    publicado = salvar_saida_publica((linha + "\n").encode(), tmp_path / "docs/log.jsonl", tmp_path)
    assert len(publicado.splitlines()) == 1
    assert json.loads(publicado) == {"caminho": "./arquivo"}


def test_prefixo_posix_nao_altera_url_ou_diretorio_parecido():
    texto = "https://exemplo.org/app/x /opt/app/x /app/x"
    assert sanitizar_caminhos(texto, PurePosixPath("/app"), PurePosixPath("/")) == (
        "https://exemplo.org/app/x /opt/app/x ./x"
    )


def test_jsonl_preserva_separador_unicode_e_json_preserva_surrogate(tmp_path):
    linha = json.dumps(
        {"caminho": str(tmp_path), "texto": "a\u2028b", "byte": "\udc80"}, ensure_ascii=True
    )
    linha = linha.replace(r"\u2028", "\u2028")
    publicado = salvar_saida_publica(linha.encode(), tmp_path / "docs/log.jsonl", tmp_path)
    dados = json.loads(publicado)
    assert dados == {"caminho": ".", "texto": "a\u2028b", "byte": "\udc80"}
