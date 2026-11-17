"""Copia somente evidências agregadas de uma execução local concluída."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from credito_monitorado.publicacao import salvar_saida_publica


def export_evidence(source: Path, destination: Path) -> None:
    """Exclui dataset, IDs de clientes, predições individuais, modelo e banco."""
    summary = json.loads((source / "resumo.json").read_text(encoding="utf-8"))
    if summary.get("status") != "sucesso":
        raise ValueError("Somente execução concluída com sucesso pode ser exportada.")
    if destination.exists():
        raise ValueError("Use um destino novo para preservar evidências anteriores.")
    names = ["index.html", "resumo.json", "manifesto.json", "logs.jsonl", "alertas.json"]
    for scenario in summary["scenarios"]:
        names.extend(
            f"{scenario}/{filename}"
            for filename in ("evidently.html", "evidently.json", "monitoring.json")
        )
    for name in names:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        salvar_saida_publica(
            (source / name).read_bytes(), target, Path(__file__).resolve().parents[1]
        )
    hashes = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest() for name in names}
    manifest = {
        "execution_id": summary["execution_id"],
        "source_status": summary["status"],
        "included_sha256": hashes,
        "excluded": ["modelo.joblib", "dados brutos", "predições individuais", "banco MLflow"],
        "note": (
            "O manifesto original descreve a execução local completa. "
            "Este inventário descreve somente os arquivos agregados incluídos no Git. "
            "As cópias publicadas têm caminhos locais sanitizados; os hashes do manifesto "
            "original continuam descrevendo os artefatos privados da execução. "
            "O banco MLflow e o modelo devem ser recriados executando o pipeline."
        ),
    }
    (destination / "publicacao.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Evidências agregadas exportadas: {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origem", type=Path)
    parser.add_argument("destino", type=Path)
    args = parser.parse_args()
    export_evidence(args.origem.resolve(), args.destino.resolve())


if __name__ == "__main__":
    main()
