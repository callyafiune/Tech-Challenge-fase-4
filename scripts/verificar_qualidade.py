"""Registra a suíte local separadamente, sem alterar as evidências do Docker."""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Preserva os bytes dos logs, os horários e o código de saída de cada comando."""
    indice = {
        "inicio_utc": datetime.now(UTC).isoformat(),
        "coletor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "comandos": [],
    }
    comandos = [
        ("ruff", ["uv", "run", "ruff", "check", "."]),
        ("formato", ["uv", "run", "ruff", "format", "--check", "."]),
        ("pytest", ["uv", "run", "pytest", "-q"]),
    ]
    for nome, comando in comandos:
        inicio = datetime.now(UTC).isoformat()
        resultado = subprocess.run(
            comando, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900
        )
        caminho = ROOT / f"docs/validacao/docker-qualidade-final-{nome}.log"
        caminho.write_bytes(resultado.stdout)
        indice["comandos"].append(
            {
                "comando": comando,
                "inicio_utc": inicio,
                "fim_utc": datetime.now(UTC).isoformat(),
                "codigo_saida": resultado.returncode,
                "saida_esperada": 0,
                "log": caminho.relative_to(ROOT / "docs").as_posix(),
                "log_sha256": hashlib.sha256(resultado.stdout).hexdigest(),
            }
        )
        indice["fim_utc"] = datetime.now(UTC).isoformat()
        (ROOT / "docs/validacao/docker-qualidade-final.json").write_bytes(
            (json.dumps(indice, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
        print(f"{nome}: saída {resultado.returncode}", flush=True)
        if resultado.returncode:
            raise SystemExit(resultado.returncode)


if __name__ == "__main__":
    main()
