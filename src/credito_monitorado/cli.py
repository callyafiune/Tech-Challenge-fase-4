"""Interface de linha de comando da demonstração de confiabilidade."""

import argparse
import sys
from pathlib import Path

from credito_monitorado.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    """Conclui com código não zero em falhas, sem divulgar dados ou exceções brutas."""
    parser = argparse.ArgumentParser(
        description="Monitoramento local de crédito e drift sintético."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Executar a demonstração completa.")
    run.add_argument("--config", type=Path, default=Path("params.yaml"))
    run.add_argument("--output", type=Path, default=Path("artifacts"))
    run.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    run.add_argument("--tracking-uri", default=None)
    arguments = parser.parse_args(argv)
    try:
        result = run_pipeline(
            arguments.config, arguments.output, arguments.data_dir, arguments.tracking_uri
        )
    except (Exception, KeyboardInterrupt) as error:
        print("Execução interrompida.", file=sys.stderr)
        output = getattr(error, "execution_output_dir", None)
        if output:
            print(f"Diretório de evidências da execução: {output}", file=sys.stderr)
        else:
            print("Não foi possível identificar um diretório de evidências.", file=sys.stderr)
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    print(f"Execução concluída: {result['execution_id']}")
    print(f"Relatório: {Path(result['output_dir']) / 'index.html'}")
    print(f"Resumo: {Path(result['output_dir']) / 'resumo.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
