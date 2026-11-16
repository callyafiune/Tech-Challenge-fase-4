"""Registra verificações literais vinculadas ao código e a uma execução real."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

from credito_monitorado.pipeline import _source_identity


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_execution(summary_path: Path, root: Path, source_identity: dict) -> dict:
    """Confere bytes, identidade e configuração sem depender do estado de staging do Git."""
    summary_path = Path(summary_path).absolute()
    execution_dir = summary_path.parent.resolve()
    manifest_path = execution_dir / "manifesto.json"
    try:
        if not summary_path.resolve().is_relative_to(execution_dir):
            raise ValueError("O resumo deve permanecer no diretório da execução.")
        if not manifest_path.resolve().is_relative_to(execution_dir):
            raise ValueError("O manifesto deve permanecer no diretório da execução.")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if summary["execution_id"] != execution_dir.name or summary["status"] != "sucesso":
            raise ValueError("A identidade do diretório e o sucesso da execução são obrigatórios.")
        source_matches = all(
            summary["source"][key] == source_identity[key]
            for key in ("files_sha256", "source_sha256")
        )
        if not source_matches:
            raise ValueError("As fontes atuais não correspondem aos bytes da execução.")
        config = yaml.safe_load((Path(root) / "params.yaml").read_text(encoding="utf-8"))
        config_hash = _sha256(
            json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")
        )
        if summary["config_sha256"] != config_hash or summary["config"] != config:
            raise ValueError("A configuração atual não corresponde à execução.")
        for key in ("execution_id", "status", "source", "config_sha256"):
            if manifest.get(key) != summary[key]:
                raise ValueError("O manifesto diverge do resumo da execução.")
        for key, value in manifest.items():
            if key not in {"artifacts_sha256", "scenarios"} and value != summary.get(key):
                raise ValueError("O manifesto contém metadados divergentes do resumo.")
        scenario_keys = ("rows", "ids_sha256", "data_sha256", "features_sha256", "simulation")
        scenarios = {
            name: {key: values[key] for key in scenario_keys if key in values}
            for name, values in summary["scenarios"].items()
        }
        if manifest.get("scenarios") != scenarios:
            raise ValueError("Os cenários do manifesto divergem do resumo.")
        hashes = manifest["artifacts_sha256"]
        if not isinstance(hashes, dict) or summary_path.name not in hashes:
            raise ValueError("O manifesto precisa incluir os hashes dos artefatos e do resumo.")
        for relative, expected in hashes.items():
            path = execution_dir / relative
            if Path(relative).is_absolute() or not path.resolve().is_relative_to(execution_dir):
                raise ValueError("O manifesto contém um caminho fora da execução.")
            if not path.is_file() or _sha256(path.read_bytes()) != expected:
                raise ValueError("Um artefato está ausente ou foi adulterado.")
        actual_files = {
            path.relative_to(execution_dir).as_posix()
            for path in execution_dir.rglob("*")
            if path.is_file() and path != manifest_path
        }
        if actual_files != set(hashes):
            raise ValueError("Há artefatos fora do manifesto ou caminhos não canônicos.")
    except (OSError, KeyError, TypeError, AttributeError, json.JSONDecodeError, yaml.YAMLError):
        raise ValueError("Não foi possível validar a evidência da execução.") from None
    return {
        "summary": summary,
        "current_source_sha256": source_identity["source_sha256"],
        "source_matches": source_matches,
        "manifesto_sha256": _sha256(manifest_path.read_bytes()),
        "artifacts_sha256": hashes,
        "config_sha256": config_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resumo", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        validation = validate_execution(args.resumo, root, _source_identity())
    except ValueError as error:
        raise SystemExit(str(error)) from None
    summary = validation["summary"]
    destination = root / "docs" / "validacao"
    destination.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    records = []
    environment = {**os.environ, "PYTHONUTF8": "1"}
    commands = [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "pytest", "-q", "--junitxml=docs/validacao/pytest.xml"],
        ["git", "diff", "--check"],
        ["git", "diff", "--cached", "--check"],
        ["uv", "run", "ruff", "check", ".", "--show-files"],
        ["uv", "run", "ruff", "format", "--check", "--verbose", "."],
    ]
    for index, command in enumerate(commands, start=1):
        begin = datetime.now(UTC)
        completed = subprocess.run(command, cwd=root, env=environment, capture_output=True)
        log_path = destination / f"{index:02d}-comando.log"
        content = completed.stdout + completed.stderr
        log_path.write_bytes(content)
        records.append(
            {
                "comando": " ".join(command),
                "inicio_utc": begin.isoformat(),
                "fim_utc": datetime.now(UTC).isoformat(),
                "codigo_saida": completed.returncode,
                "saida_literal": content.decode("utf-8", errors="replace"),
                "arquivo": log_path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    record = {
        "inicio_utc": started.isoformat(),
        "fim_utc": datetime.now(UTC).isoformat(),
        "source_sha256": summary["source"]["source_sha256"],
        "current_source_sha256": validation["current_source_sha256"],
        "source_matches": validation["source_matches"],
        "execution_id": summary["execution_id"],
        "execucao_real": {
            "command_reference": "não capturado da CLI original",
            "cli_exit_code": "não capturado da CLI original",
            "comando_para_reproducao": (
                "uv run python -X utf8 -m credito_monitorado.cli run "
                "--config params.yaml --output artifacts"
            ),
            "status": summary["status"],
            "origem_do_status": "derivado do resumo produzido pelo pipeline",
            "inicio_utc": summary["started_at_utc"],
            "duracao_segundos": summary["duration_seconds"],
            "manifesto_sha256": validation["manifesto_sha256"],
            "artifacts_sha256": validation["artifacts_sha256"],
            "config_sha256": validation["config_sha256"],
            "alertas": len(summary["alerts"]),
            "drift_por_cenario": {
                name: scenario["drift"]["summary"]["drifted_features"]
                for name, scenario in summary["scenarios"].items()
            },
        },
        "observacao_descoberta_ruff": (
            "Ruff format inclui arquivos .md; ruff check --show-files lista Python/TOML. "
            "A descoberta do format está capturada literalmente no comando 7 com --verbose."
        ),
        "evidencias_adicionais_sha256": {
            name: _sha256((root / name).read_bytes())
            for name in ("docs/validacao/pytest.xml", "docs/evidencias_mlflow.json")
            if (root / name).is_file()
        },
        "comandos": records,
        "resultado": "aprovado" if all(r["codigo_saida"] == 0 for r in records) else "falha",
    }
    (root / "docs" / "verificacao.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Verificações registradas: {record['resultado']}.")
    raise SystemExit(0 if record["resultado"] == "aprovado" else 1)


if __name__ == "__main__":
    main()
