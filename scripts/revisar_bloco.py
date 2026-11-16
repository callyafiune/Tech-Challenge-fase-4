"""Submete um bloco à revisão adversarial independente no Claude Code Fable."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    """Grava parecer e evidência do modelo efetivamente utilizado."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bloco")
    parser.add_argument("arquivos", nargs="+")
    parser.add_argument("--foco", default="Revisão integral do bloco fornecido.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    executable = shutil.which("claude")
    if executable is None:
        raise SystemExit("Claude Code não encontrado no PATH.")
    sections = []
    fingerprints = {}
    for name in args.arquivos:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise SystemExit("O pacote de revisão deve estar dentro do repositório.")
        sections.append(f"\n### Arquivo: {name}\n```\n{path.read_text(encoding='utf-8')}\n```\n")
        fingerprints[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    prompt = (
        "Você é revisor adversarial independente deste Tech Challenge. "
        "Responda em português Brasil. "
        "Não implemente nem execute ações. Examine criticamente somente o pacote abaixo: "
        "correção, aderência aos requisitos, vazamento treino/teste, validade estatística, "
        "privacidade, reprodutibilidade, falhas e cobertura. Priorize defeitos concretos e "
        "reproduzíveis; indique arquivo/função, impacto e correção. Separe críticos, importantes "
        "e menores. Se não houver defeitos diga explicitamente. Termine com veredito de "
        "conformidade e qualidade. Não aceite alegações da documentação como prova de execução. "
        "O vídeo foi excluído do escopo pelo usuário: apenas roteiro.\n"
        f"Foco desta rodada: {args.foco}\n" + "\n".join(sections)
    )
    command = [
        executable,
        "-p",
        "--model",
        "fable",
        "--effort",
        "high",
        "--output-format",
        "json",
        "--safe-mode",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--tools",
        "",
    ]
    result = subprocess.run(
        command,
        input=prompt,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=root,
        timeout=900,
    )
    destination = root / "docs" / "revisoes"
    destination.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise SystemExit(
            f"Revisão sem resposta JSON válida (código {result.returncode})."
        ) from None
    metadata = {
        key: payload.get(key)
        for key in ("session_id", "duration_ms", "num_turns", "is_error", "subtype")
    }
    metadata["modelos"] = list(payload.get("modelUsage", {}))
    metadata["velocidade"] = payload.get("usage", {}).get("speed", "standard")
    metadata["instante_utc"] = dt.datetime.now(dt.UTC).isoformat()
    metadata["arquivos"] = args.arquivos
    metadata["sha256"] = fingerprints
    metadata["foco"] = args.foco
    metadata["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    destination.joinpath(f"{args.bloco}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    destination.joinpath(f"{args.bloco}.md").write_text(
        f"# Revisão adversarial — {args.bloco}\n\n"
        f"Modelo solicitado: `fable`. Modelo retornado: `{', '.join(metadata['modelos'])}`.\n\n"
        + payload.get("result", "Sem parecer retornado.")
        + "\n",
        encoding="utf-8",
    )
    print(f"Parecer gravado em docs/revisoes/{args.bloco}.md")
    if result.returncode or payload.get("is_error"):
        raise SystemExit("A revisão falhou; consulte os registros do bloco.")


if __name__ == "__main__":
    main()
