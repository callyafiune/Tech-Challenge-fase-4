"""Orquestra a demonstração local com evidências agregadas e falhas explícitas."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from credito_monitorado.config import load_config
from credito_monitorado.contracts import FEATURES, DataContractError, validate_batch
from credito_monitorado.data import acquire_dataset, load_dataset, split_dataset
from credito_monitorado.drift import build_scenarios
from credito_monitorado.model import evaluate_model, predict, train_baseline
from credito_monitorado.monitoring import compare_concept, evaluate_scenario
from credito_monitorado.reporting import render_summary
from credito_monitorado.telemetry import Telemetry, write_json
from credito_monitorado.tracking import (
    finalize_tracking,
    sync_tracking_artifacts,
    track_execution,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _table_hash(frame: pd.DataFrame) -> str:
    """Inclui nomes, ordem das colunas e valores, sem persistir registros."""
    schema = json.dumps(list(frame.columns), ensure_ascii=False).encode("utf-8")
    content = pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes()
    return _digest(schema + content)


def _identities(frame: pd.DataFrame) -> dict:
    ordered = frame.sort_values("record_id").reset_index(drop=True)
    return {
        "rows": len(frame),
        "ids_sha256": _table_hash(ordered[["record_id"]]),
        "data_sha256": _table_hash(ordered),
        "features_sha256": _table_hash(frame[FEATURES]),
        "class_rate": (
            float(frame["target"].mean())
            if "target" in frame and frame["target"].notna().any()
            else None
        ),
    }


def _versions() -> dict:
    versions = {"python": platform.python_version()}
    for name in ("pandas", "numpy", "scikit-learn", "pandera", "evidently", "mlflow", "scipy"):
        versions[name] = importlib.metadata.version(name)
    return versions


def _git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def _safe_tracking_uri(uri: str) -> str:
    """Omite destinos remotos e preserva somente o caminho de bancos SQLite locais."""
    if uri.lower().startswith("sqlite:"):
        return uri.split("?", 1)[0].split("#", 1)[0]
    return "destino_remoto_omitido"


def _source_identity() -> dict:
    """Identifica o código local inclusive quando há alterações fora do HEAD."""
    files = {
        path
        for directory in ("src", "tests", "scripts")
        for path in (PROJECT_ROOT / directory).rglob("*.py")
        if path.is_file()
    }
    files.update(
        path
        for name in (
            "params.yaml",
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            ".gitattributes",
            ".github/workflows/ci.yml",
        )
        if (path := PROJECT_ROOT / name).is_file()
    )
    hashes = {
        path.relative_to(PROJECT_ROOT).as_posix(): _digest(path.read_bytes())
        for path in sorted(files)
    }
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        dirty = bool(status.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        dirty = None
    return {
        "git_dirty": dirty,
        "files_sha256": hashes,
        "source_sha256": _digest(json.dumps(hashes, sort_keys=True).encode("utf-8")),
    }


def _verify_partitions(parts: dict[str, pd.DataFrame], dataset: pd.DataFrame) -> None:
    """Confere exclusão mútua e cobertura antes de aceitar o resultado do splitter."""
    if set(parts) != {"train", "validation", "reference", "production_pool"}:
        raise RuntimeError("As partições obrigatórias não estão completas.")
    seen = set()
    for frame in parts.values():
        current = set(frame["record_id"])
        if len(current) != len(frame) or seen.intersection(current):
            raise RuntimeError("As partições possuem identidades sobrepostas ou duplicadas.")
        seen.update(current)
    if seen != set(dataset["record_id"]) or sum(map(len, parts.values())) != len(dataset):
        raise RuntimeError("As partições não cobrem exclusivamente a base validada.")


def _contract_demo(frame: pd.DataFrame, telemetry: Telemetry) -> dict:
    """Rejeita o lote combinado e prova cada regra isolada sem chamar o modelo."""
    base = frame.iloc[:10].copy(deep=True).reset_index(drop=True)
    # Mantém o dtype da variante nula igual ao controle numérico positivo.
    base["limit_bal"] = base["limit_bal"].astype(float)
    with telemetry.stage("contrato_controle_positivo", len(base)):
        validate_batch(base, require_target=False)
    variants = {}
    for name in ("nulo", "idade", "duplicidade"):
        invalid = base.copy(deep=True)
        if name == "nulo":
            invalid.loc[0, "limit_bal"] = np.nan
        elif name == "idade":
            invalid.loc[1, "age"] = 17
        else:
            invalid.loc[2, "record_id"] = invalid.loc[3, "record_id"]
        variants[name] = invalid
    combined = variants["nulo"].copy(deep=True)
    combined.loc[1, "age"] = 17
    combined.loc[2, "record_id"] = combined.loc[3, "record_id"]
    variants["combinado"] = combined
    rules = []
    for name, invalid in variants.items():
        try:
            with telemetry.stage(f"contrato_invalido_{name}", len(invalid), expected_failure=True):
                validate_batch(invalid, require_target=False)
        except DataContractError:
            rules.append({"rule": name, "blocked": True, "rejected_rows": len(invalid)})
        else:
            raise RuntimeError("A demonstração não rejeitou uma violação esperada do contrato.")
    telemetry.alert(
        "BLOQUEIO_CONTRATO",
        "aviso",
        "lote_invalido",
        "Lote de demonstração rejeitado integralmente antes da inferência.",
        observed=len(combined),
        threshold=0,
        recommended_action="Corrigir a origem e validar novamente o lote completo.",
    )
    return {
        "status": "blocked_as_expected",
        "rows_received": len(combined),
        "rejected_rows": len(combined),
        "inference_calls": 0,
        "inference_calls_evidence": "garantia_do_fluxo_sem_contador_instrumentado",
        "positive_control_validated": True,
        "rules": rules,
    }


def _scenario_alerts(name: str, result: dict, config: dict, telemetry: Telemetry) -> None:
    settings = config["monitoring"]
    drift = result["drift"]["summary"]
    count = len(drift["drifted_features"])
    if drift["drift_detected"]:
        telemetry.alert(
            "DRIFT_ENTRADAS",
            "aviso",
            name,
            "Atributos ultrapassaram a política estatística configurada; investigar entradas.",
            observed=count,
            threshold=1,
            recommended_action=(
                "Revisar distribuição, coleta e seleção; drift de X não prova conceito."
            ),
        )
    current = result.get("performance")
    reference = result.get("reference_performance")
    if current is None or reference is None:
        telemetry.alert(
            "ROTULOS_PENDENTES",
            "aviso",
            name,
            "Métricas supervisionadas pendentes por indisponibilidade de rótulos.",
            recommended_action="Aguardar rótulos observados e verificar sua cobertura e atraso.",
        )
        return
    for metric, code, threshold, direction in (
        ("roc_auc", "QUEDA_AUROC", settings["auc_drop_threshold"], -1),
        ("brier_score", "AUMENTO_BRIER", settings["brier_increase_threshold"], 1),
    ):
        if current.get(metric) is None or reference.get(metric) is None:
            continue
        difference = direction * (current[metric] - reference[metric])
        if difference >= threshold:
            telemetry.alert(
                code,
                "critico",
                name,
                "Degradação supervisionada material em relação à referência congelada.",
                observed=difference,
                threshold=threshold,
                recommended_action=(
                    "Investigar rótulos, seleção e desempenho; exigir revisão humana."
                ),
            )


def _persist(summary: dict, telemetry: Telemetry, output: Path, start: float) -> None:
    summary.update(
        duration_seconds=round(time.perf_counter() - start, 6),
        events=telemetry.events,
        alerts=telemetry.alerts,
        resources=telemetry.resources,
    )
    write_json(output / "alertas.json", telemetry.alerts)
    write_json(output / "resumo.json", summary)
    manifest = {
        key: summary.get(key)
        for key in (
            "execution_id",
            "started_at_utc",
            "status",
            "duration_seconds",
            "config_sha256",
            "dataset",
            "partitions",
            "model",
            "versions",
            "git_revision",
            "source",
            "tracking",
            "resources",
            "contracts",
            "fairness",
            "failure",
            "finalization",
        )
    }
    manifest["scenarios"] = {
        name: {
            key: result[key]
            for key in ("rows", "ids_sha256", "data_sha256", "features_sha256", "simulation")
            if key in result
        }
        for name, result in summary["scenarios"].items()
    }
    render_summary(summary, output)
    manifest["artifacts_sha256"] = {
        path.relative_to(output).as_posix(): _digest(path.read_bytes())
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifesto.json"
    }
    write_json(output / "manifesto.json", manifest)


def _verify_artifacts(summary: dict, output: Path) -> None:
    expected = [
        "modelo.joblib",
        "resumo.json",
        "manifesto.json",
        "logs.jsonl",
        "alertas.json",
        "index.html",
    ]
    for name, result in summary["scenarios"].items():
        expected.extend(
            [f"{name}/{result['evidently_html']}", f"{name}/{result['aggregate_json']}"]
        )
    if any(
        not (output / filename).is_file() or not (output / filename).stat().st_size
        for filename in expected
    ):
        raise RuntimeError("Uma evidência obrigatória da execução está ausente ou vazia.")


def _refresh_snapshot(summary: dict, telemetry: Telemetry, output: Path, start: float) -> None:
    """Fecha o retrato após medir uma etapa; falhas de publicação recebem evento próprio."""
    try:
        _persist(summary, telemetry, output, start)
    except BaseException:
        with telemetry.stage("finalizacao_artefatos"):
            raise


def run_pipeline(
    config_path: Path,
    output_dir: Path,
    data_dir: Path = Path("data/raw"),
    tracking_uri: str | None = None,
) -> dict:
    """Executa os quatro cenários; preserva resumo seguro e relança falhas inesperadas."""
    start = time.perf_counter()
    started = datetime.now(UTC)
    execution_id = f"{started:%Y%m%dT%H%M%S}_{uuid.uuid4().hex[:12]}"
    output = Path(output_dir).resolve() / execution_id
    output.mkdir(parents=True, exist_ok=False)
    telemetry = Telemetry(output)
    summary = {
        "execution_id": execution_id,
        "started_at_utc": started.isoformat(),
        "status": "em_execucao",
        "output_dir": str(output),
        "config": {},
        "config_sha256": None,
        "dataset": {},
        "partitions": {},
        "model": {},
        "scenarios": {},
        "concept": {},
        "tracking": {},
        "versions": {},
        "git_revision": _git_revision(),
    }
    uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI")
    summary["tracking"] = {"status": "pending"}
    try:
        with telemetry.stage("configuracao"):
            if uri is None:
                database = PROJECT_ROOT / "artifacts" / "mlflow.db"
                database.parent.mkdir(parents=True, exist_ok=True)
                uri = f"sqlite:///{database.as_posix()}"
            summary["tracking"]["uri"] = _safe_tracking_uri(uri)
            summary["versions"] = _versions()
            summary["source"] = _source_identity()
            config = load_config(Path(config_path))
            summary["config"] = config
            summary["config_sha256"] = _digest(
                json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")
            )
        with telemetry.stage("aquisicao"):
            dataset_path = acquire_dataset(Path(data_dir))
        with telemetry.stage("validacao_origem"):
            dataset = load_dataset(dataset_path, min_rows=config["dataset"]["min_rows"])
            if len(dataset) < config["dataset"]["min_rows"]:
                raise RuntimeError("O dataset não atende ao volume mínimo configurado.")
            provenance = json.loads((dataset_path.parent / "manifest.json").read_text("utf-8"))
            summary["dataset"] = {
                **provenance,
                "sha256": _digest(dataset_path.read_bytes()),
                "rows": len(dataset),
                "size_bytes": dataset_path.stat().st_size,
                "normalized_data_sha256": _table_hash(dataset),
            }
        with telemetry.stage("particionamento", len(dataset)):
            parts = split_dataset(dataset, config["seed"])
            _verify_partitions(parts, dataset)
            summary["partitions"] = {name: _identities(frame) for name, frame in parts.items()}
        summary["contracts"] = _contract_demo(parts["production_pool"], telemetry)
        with telemetry.stage("treinamento", len(parts["train"])):
            trained = train_baseline(parts["train"], parts["validation"], config)
            if not (
                trained.metrics["roc_auc"] > 0.65
                and trained.metrics["roc_auc"] > trained.metrics["dummy_roc_auc"]
            ):
                raise RuntimeError("O baseline não atende à porta de desempenho da validação.")
        with telemetry.stage("persistencia_modelo", len(parts["validation"])):
            model_path = output / "modelo.joblib"
            bundle = {
                "pipeline": trained.pipeline,
                "threshold": trained.threshold,
                "features": FEATURES,
            }
            joblib.dump(bundle, model_path)
            reloaded = joblib.load(model_path)
            before = predict(trained.pipeline, parts["validation"], trained.threshold)
            after = predict(reloaded["pipeline"], parts["validation"], reloaded["threshold"])
            if not before.equals(after):
                raise RuntimeError("A persistência alterou as predições do modelo.")
            model = reloaded["pipeline"]
            summary["model"] = {
                "threshold": trained.threshold,
                "validation_metrics": trained.metrics,
                "sha256": _digest(model_path.read_bytes()),
                "features": FEATURES,
                "roundtrip_predictions_equal": True,
                "hyperparameters": config["model"],
                "trained_only_on": "train",
            }
            reference_prediction = predict(model, parts["reference"], trained.threshold)
            summary["model"]["reference_metrics"] = evaluate_model(
                parts["reference"]["target"], reference_prediction["probability"], trained.threshold
            )
        with telemetry.stage("geracao_cenarios", len(parts["production_pool"])):
            scenarios = build_scenarios(parts["production_pool"], parts["reference"], config)
        for window_index, (name, frame) in enumerate(scenarios.items()):
            with telemetry.stage(f"monitoramento_{name}", len(frame)):
                result = evaluate_scenario(
                    parts["reference"], frame, model, trained.threshold, output / name, config
                )
                result.update(_identities(frame), simulation=frame.attrs.get("simulation", {}))
                result.update(
                    execution_id=execution_id,
                    scenario=name,
                    config_sha256=summary["config_sha256"],
                    model_sha256=summary["model"]["sha256"],
                    simulated_window=f"T{window_index}",
                    window_index=window_index,
                )
                write_json(output / name / result["aggregate_json"], result)
                summary["scenarios"][name] = result
                _scenario_alerts(name, result, config, telemetry)
        with telemetry.stage("comparacao_conceito", len(scenarios["control"])):
            control_p = predict(model, scenarios["control"], trained.threshold)["probability"]
            concept_p = predict(model, scenarios["concept"], trained.threshold)["probability"]
            concept = compare_concept(
                scenarios["control"], scenarios["concept"], control_p, concept_p, config
            )
            summary["concept"] = concept
            if not concept["same_features"] or not concept["same_predictions"]:
                raise RuntimeError(
                    "A simulação de conceito violou os invariantes do contrafactual."
                )
            if concept["conditional_change_evidence"]:
                telemetry.alert(
                    "CONCEITO_SIMULADO",
                    "critico",
                    "concept",
                    "A intervenção conhecida nos rótulos gerou degradação pareada material.",
                    observed=concept["brier_increase"],
                    threshold=concept["effect_threshold"],
                    recommended_action=(
                        "Validar o experimento; em produção investigar causas e rótulos."
                    ),
                )
            covariate_p = predict(model, scenarios["covariate"], trained.threshold)["probability"]
            combined_p = predict(model, scenarios["combined"], trained.threshold)["probability"]
            combined_comparison = compare_concept(
                scenarios["covariate"], scenarios["combined"], covariate_p, combined_p, config
            )
            summary["concept_combined"] = combined_comparison
            if (
                not combined_comparison["same_features"]
                or not combined_comparison["same_predictions"]
            ):
                raise RuntimeError("O cenário combinado violou os invariantes do contrafactual.")
        with telemetry.stage("auditoria_grupos", len(parts["reference"])):
            from credito_monitorado.fairness import audit_groups

            reference_p = predict(model, parts["reference"], trained.threshold)["probability"]
            summary["fairness"] = audit_groups(parts["reference"], reference_p, trained.threshold)
        with telemetry.stage("preparacao_relatorio"):
            _persist(summary, telemetry, output, start)
            _verify_artifacts(summary, output)
        with telemetry.stage("rastreamento_mlflow"):
            run_id = track_execution(summary, output, uri)
            summary["tracking"].update(run_id=run_id, status="completed")
        with telemetry.stage("finalizacao_artefatos"):
            telemetry.check_health(
                config["monitoring"]["max_stage_seconds"], config["monitoring"]["max_rss_mb"]
            )
            summary["status"] = "sucesso"
            summary["finalization"] = {
                "duration_scope": (
                    "Inclui a sincronização medida; exclui a cópia final dos snapshots."
                ),
                "snapshot_publication": "Cópia de fechamento sem reabrir a medição de si própria.",
            }
            _persist(summary, telemetry, output, start)
            _verify_artifacts(summary, output)
        _refresh_snapshot(summary, telemetry, output, start)
        with telemetry.stage("sincronizacao_mlflow"):
            finalize_tracking(summary, output, uri)
        _refresh_snapshot(summary, telemetry, output, start)
        try:
            sync_tracking_artifacts(summary, output, uri)
        except BaseException:
            with telemetry.stage("publicacao_final_mlflow"):
                raise
        return summary
    except BaseException as error:
        summary["status"] = "falha"
        summary["failure"] = {
            "error_type": type(error).__name__,
            "message": "Falha operacional; consulte etapas e contagens agregadas.",
        }
        failures = [
            event
            for event in telemetry.events
            if event["status"] == "falha" and not event.get("expected_failure")
        ]
        summary["failure"]["failed_stage"] = failures[-1]["stage"] if failures else "pipeline"
        try:
            error.execution_output_dir = str(output)
        except BaseException:
            pass
        if any(event["stage"] == "rastreamento_mlflow" for event in telemetry.events):
            summary["tracking"]["status"] = "failed"
        if summary["tracking"].get("run_id"):
            summary["tracking"]["status"] = "failed"
            try:
                from mlflow.tracking import MlflowClient

                MlflowClient(tracking_uri=uri).set_terminated(
                    summary["tracking"]["run_id"], "FAILED"
                )
            except BaseException:
                summary["tracking"]["failure_status_sync"] = "failed"
        try:
            telemetry.alert(
                "FALHA_EXECUCAO",
                "critico",
                "pipeline",
                "A execução foi interrompida por falha operacional.",
            )
        except BaseException:
            pass
        try:
            _persist(summary, telemetry, output, start)
        except BaseException:
            minimal = {
                "execution_id": execution_id,
                "status": "falha",
                "failure": summary["failure"],
                "output_dir": str(output),
            }
            try:
                write_json(output / "falha.json", minimal)
            except BaseException:
                pass
        raise
