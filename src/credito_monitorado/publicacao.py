"""Remove caminhos da máquina das evidências destinadas ao Git."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def sanitizar_caminhos(texto: str, raiz: Path, usuario: Path | None = None) -> str:
    """Substitui prefixos conhecidos, incluindo separadores escapados em JSON."""
    if usuario is None:
        try:
            usuario = Path.home()
        except RuntimeError:
            usuario = raiz
    for caminho, substituto in ((raiz, "."), (usuario, "[USUARIO]")):
        partes = re.split(r"[\\/]+", str(caminho).rstrip("\\/"))
        if not any(partes):
            continue
        prefixo = r"[\\/]+".join(re.escape(parte) for parte in partes)
        padrao = (
            rf"(?<![\w.\\/-])(?:(?:file|sqlite):///)?{prefixo}"
            rf"(?P<barra>[\\/]+|(?!(?:[\w-]|\.\w)))"
        )
        texto = re.sub(
            padrao,
            lambda match, marca=substituto: marca + ("/" if match["barra"] else ""),
            texto,
            flags=re.IGNORECASE if caminho.drive else 0,
        )
    return texto


def _sanitizar_json(valor, raiz: Path):
    """Trata strings decodificadas para preservar escapes e estruturas aninhadas."""
    if isinstance(valor, dict):
        return {
            sanitizar_caminhos(key, raiz): _sanitizar_json(item, raiz)
            for key, item in valor.items()
        }
    if isinstance(valor, list):
        return [_sanitizar_json(item, raiz) for item in valor]
    if isinstance(valor, str):
        return _sanitizar_texto(valor, raiz)
    return valor


def _sanitizar_texto(texto: str, raiz: Path, compacto: bool = False) -> str:
    try:
        original = json.loads(texto)
    except (ValueError, RecursionError):
        return sanitizar_caminhos(texto, raiz)
    revisado = _sanitizar_json(original, raiz)
    return (
        json.dumps(revisado, ensure_ascii=True, indent=None if compacto else 2)
        if revisado != original
        else texto
    )


def salvar_saida_publica(conteudo: bytes, destino: Path, raiz: Path) -> bytes:
    """Guarda o original privado e publica uma cópia com caminhos sanitizados."""
    texto = conteudo.decode("utf-8", errors="surrogateescape")
    if destino.suffix == ".jsonl":
        texto = "\n".join(
            _sanitizar_texto(linha, raiz, compacto=True) for linha in texto.split("\n")
        )
    else:
        texto = _sanitizar_texto(texto, raiz)
    if destino.suffix == ".xml":
        texto = re.sub(r'hostname="[^"]*"', 'hostname="[MAQUINA]"', texto)
    publicado = texto.encode("utf-8", errors="surrogateescape")
    if publicado != conteudo:
        digest = hashlib.sha256(conteudo).hexdigest()
        privado = raiz / "artifacts/evidencias_privadas" / digest / destino.name
        privado.parent.mkdir(parents=True, exist_ok=True)
        privado.write_bytes(conteudo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(publicado)
    return publicado
