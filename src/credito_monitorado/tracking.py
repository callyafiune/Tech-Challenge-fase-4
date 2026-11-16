"""Rastreia experimento e cenários em MLflow local com artefatos agregados."""

from __future__ import annotations

import math
import os
from pathlib import Path


def _finite_metrics(values: dict) -> dict[str, float]:
    """Exclui métricas indefinidas, mantendo seus motivos no resumo JSON."""
    return {
        key: float(value)
        for key, value in values.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    }


def track_execution(summary: dict, artifacts_dir: Path, tracking_uri: str) -> str:
    """Cria um run pai e um filho por cenário; falhas de rastreamento são fatais."""
    os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    experiment_name = summary["config"]["tracking"]["experiment_name"]
    artifact_root = artifacts_dir.parent / "mlflow-artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    if mlflow.get_experiment_by_name(experiment_name) is None:
        mlflow.create_experiment(experiment_name, artifact_location=artifact_root.as_uri())
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=summary["execution_id"]) as parent:
        mlflow.set_tags({"dominio": "credito", "fase": "4", "dados": "UCI-350"})
        mlflow.log_params(
            {
                "seed": summary["config"]["seed"],
                "limiar": summary["model"]["threshold"],
                "dataset_sha256": summary["dataset"]["sha256"],
                "config_sha256": summary["config_sha256"],
                "modelo_sha256": summary["model"]["sha256"],
            }
        )
        mlflow.log_metrics(_finite_metrics(summary["model"]["validation_metrics"]))
        mlflow.log_metrics(
            {
                f"referencia_{key}": value
                for key, value in _finite_metrics(
                    summary["model"].get("reference_metrics", {})
                ).items()
            }
        )
        mlflow.log_params(
            {f"modelo_{key}": value for key, value in summary["config"]["model"].items()}
        )
        mlflow.log_dict(summary["config"], "configuracao.json")
        mlflow.log_dict(summary["partitions"], "particoes.json")
        mlflow.log_artifact(str(artifacts_dir / "modelo.joblib"), artifact_path="modelo")
        for step, (name, scenario) in enumerate(summary["scenarios"].items()):
            for metric, value in _finite_metrics(scenario.get("performance") or {}).items():
                mlflow.log_metric(f"janela_{metric}", value, step=step)
            mlflow.log_metric(
                "janela_atributos_com_drift",
                len(scenario["drift"]["summary"]["drifted_features"]),
                step=step,
            )
            with mlflow.start_run(run_name=name, nested=True):
                mlflow.set_tag("rotulos", scenario["labels_status"])
                mlflow.set_tag("relatorio_run_pai", parent.info.run_id)
                if scenario.get("performance"):
                    mlflow.log_metrics(_finite_metrics(scenario["performance"]))
                mlflow.log_metric("volume", scenario["rows"])
                mlflow.log_metric(
                    "atributos_com_drift", len(scenario["drift"]["summary"]["drifted_features"])
                )
                mlflow.log_dict(scenario["drift"], "estatisticas.json")
        return parent.info.run_id


def finalize_tracking(summary: dict, artifacts_dir: Path, tracking_uri: str) -> None:
    """Sincroniza o resumo final após medir o próprio estágio de rastreamento."""
    from mlflow.tracking import MlflowClient

    client = MlflowClient(tracking_uri=tracking_uri)
    run_id = summary["tracking"]["run_id"]
    client.log_metric(run_id, "alertas", len(summary["alerts"]))
    client.log_metric(run_id, "duracao_total_segundos", summary["duration_seconds"])
    client.log_metric(run_id, "memoria_maxima_mb", max(r["rss_mb"] for r in summary["events"]))
    if summary.get("fairness"):
        client.log_dict(run_id, summary["fairness"], "observabilidade/auditoria_grupos.json")
    sync_tracking_artifacts(summary, artifacts_dir, tracking_uri)


def sync_tracking_artifacts(summary: dict, artifacts_dir: Path, tracking_uri: str) -> None:
    """Publica o retrato final e mantém os links relativos do HTML no mesmo run."""
    from mlflow.tracking import MlflowClient

    client = MlflowClient(tracking_uri=tracking_uri)
    run_id = summary["tracking"]["run_id"]
    # O último retrato já contém duração e recursos da sincronização medida.
    client.log_metric(run_id, "duracao_total_segundos", summary["duration_seconds"])
    client.log_metric(run_id, "memoria_maxima_mb", max(r["rss_mb"] for r in summary["events"]))
    client.log_metric(run_id, "alertas", len(summary["alerts"]))
    for filename in ("resumo.json", "index.html", "logs.jsonl", "alertas.json", "manifesto.json"):
        client.log_artifact(run_id, str(artifacts_dir / filename), artifact_path="observabilidade")
    for name, scenario in summary["scenarios"].items():
        for filename in (scenario["evidently_html"], scenario["aggregate_json"], "evidently.json"):
            client.log_artifact(
                run_id,
                str(artifacts_dir / name / filename),
                artifact_path=f"observabilidade/{name}",
            )
