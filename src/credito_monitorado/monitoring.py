"""Avaliação supervisionada e adapter Evidently com decisão estatística independente."""

import json
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score

from credito_monitorado.contracts import FEATURES, PAY_COLUMNS
from credito_monitorado.drift import (
    _require_disjoint_ids,
    compute_drift,
    population_stability_index,
)
from credito_monitorado.model import evaluate_model, predict


def _probabilities(values, size: int) -> np.ndarray:
    if isinstance(values, pd.DataFrame):
        values = values["probability"]
    array = np.asarray(values, dtype=float)
    if array.shape != (size,) or not np.isfinite(array).all() or ((array < 0) | (array > 1)).any():
        raise ValueError("As probabilidades devem ser finitas, alinhadas e pertencer a [0, 1].")
    return array


def _labels_available(frame: pd.DataFrame) -> bool:
    return "target" in frame and frame["target"].notna().all()


def _write_aggregate(path: Path, result: dict) -> None:
    """Substitui o JSON completo atomicamente no mesmo sistema de arquivos."""
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".monitoring-",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(serialized)
        except Exception:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _prediction_monitoring(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    reference_p: np.ndarray,
    current_p: np.ndarray,
    threshold: float,
    config: dict,
) -> dict:
    """Separa sinais de score, decisões no limiar e prevalência observada de y."""
    settings = config.get("monitoring", {})
    alpha = float(settings.get("ks_alpha", 0.05))
    effect = float(settings.get("ks_min_effect", 0.10))
    psi_threshold = float(settings.get("psi_threshold", 0.20))
    sufficient = min(len(reference_p), len(current_p)) >= int(settings.get("min_rows", 200))
    score = {
        "psi": None,
        "ks": None,
        "pvalue": None,
        "drift": None,
        "psi_drift": None,
        "ks_alpha": alpha,
        "ks_min_effect": effect,
        "psi_threshold": psi_threshold,
        "rule": "KS p <= alpha e D >= efeito mínimo; PSI é sinal complementar separado.",
        "multiplicity": "Teste único do score; não integra a família BH dos atributos de X.",
    }
    if sufficient:
        statistic = ks_2samp(reference_p, current_p)
        psi = population_stability_index(
            reference_p, current_p, epsilon=float(settings.get("psi_epsilon", 1e-6))
        )
        score.update(
            psi=psi,
            ks=float(statistic.statistic),
            pvalue=float(statistic.pvalue),
            drift=bool(statistic.pvalue <= alpha and statistic.statistic >= effect),
            psi_drift=bool(psi >= psi_threshold),
        )
    return {
        "status": "ok" if sufficient else "insufficient_sample",
        "score": score,
        "threshold": threshold,
        "reference_positive_rate": float(np.mean(reference_p >= threshold))
        if len(reference_p)
        else None,
        "current_positive_rate": float(np.mean(current_p >= threshold)) if len(current_p) else None,
        "reference_prevalence": float(reference["target"].mean())
        if _labels_available(reference) and len(reference)
        else None,
        "current_prevalence": float(current["target"].mean())
        if _labels_available(current) and len(current)
        else None,
        "interpretation": (
            "Score e taxa de decisões positivas descrevem saídas do modelo. Prevalência descreve "
            "rótulos disponíveis, que podem ser contrafactuais na simulação. Nenhum desses sinais "
            "isolados comprova alteração em P(Y|X)."
        ),
    }


def _performance(frame: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> dict | None:
    if not _labels_available(frame) or not len(frame):
        return None
    y = frame["target"].to_numpy()
    if not np.isin(y, [0, 1]).all():
        raise ValueError("Os rótulos supervisionados devem ser binários.")
    if len(np.unique(y)) < 2:
        result = {
            "status": "single_class",
            "roc_auc": None,
            "average_precision": None,
            "f1": None,
            "precision": None,
            "recall": None,
            "brier_score": float(np.mean((y - probabilities) ** 2)),
            "undefined_reason": "Classe única; métricas de discriminação não são reportadas.",
        }
    else:
        result = evaluate_model(y, probabilities, threshold)
        result["status"] = "ok"
    prediction = probabilities >= threshold
    result.update(
        label_count=len(y),
        prevalence=float(np.mean(y)),
        label_coverage=1.0,
        confusion_matrix=[
            [int(((y == 0) & ~prediction).sum()), int(((y == 0) & prediction).sum())],
            [int(((y == 1) & ~prediction).sum()), int(((y == 1) & prediction).sum())],
        ],
    )
    return result


def compare_concept(
    control: pd.DataFrame,
    concept: pd.DataFrame,
    control_probabilities,
    concept_probabilities,
    config: dict,
) -> dict:
    """Compara perdas pareadas; a interpretação depende da intervenção simulada conhecida."""
    settings = config.get("monitoring", {})
    columns = [column for column in ["record_id", *FEATURES] if column in control]
    same_features = bool(
        columns
        and all(column in concept for column in columns)
        and control[columns].reset_index(drop=True).equals(concept[columns].reset_index(drop=True))
    )
    control_p = _probabilities(control_probabilities, len(control))
    concept_p = _probabilities(concept_probabilities, len(concept))
    same_predictions = bool(np.array_equal(control_p, concept_p))
    result = {
        "status": "ok",
        "same_features": same_features,
        "same_predictions": same_predictions,
        "brier_increase": None,
        "ci95": None,
        "effect_threshold": float(settings.get("brier_increase_threshold", 0.05)),
        "bootstrap_samples": int(settings.get("bootstrap_samples", 500)),
        "bootstrap_seed": int(config.get("seed", 42)) + 4,
        "conditional_change_evidence": False,
        "interpretation": (
            "A comparação pareada contextualiza a alteração condicional simulada conhecida. "
            "Em dados reais, piora supervisionada isolada não prova mudança em P(Y|X)."
        ),
    }
    if not _labels_available(control) or not _labels_available(concept):
        result["status"] = "pending_labels"
        return result
    if not same_features or not same_predictions:
        result["status"] = "unmatched_pairs"
        return result
    if len(control) < int(settings.get("min_rows", 200)):
        result["status"] = "insufficient_sample"
        return result
    control_y = control["target"].to_numpy(dtype=float)
    concept_y = concept["target"].to_numpy(dtype=float)
    if not np.isin(control_y, [0, 1]).all() or not np.isin(concept_y, [0, 1]).all():
        raise ValueError("A comparação pareada exige rótulos binários completos.")
    difference = (concept_y - concept_p) ** 2 - (control_y - control_p) ** 2
    increase = float(np.mean(difference))
    samples = result["bootstrap_samples"]
    if samples < 1:
        raise ValueError("A quantidade de reamostragens deve ser positiva.")
    generator = np.random.default_rng(result["bootstrap_seed"])
    bootstrap = np.array(
        [
            np.mean(difference[generator.integers(0, len(difference), len(difference))])
            for _ in range(samples)
        ]
    )
    low, high = np.quantile(bootstrap, [0.025, 0.975])
    control_auc = (
        float(roc_auc_score(control_y, control_p)) if len(np.unique(control_y)) == 2 else None
    )
    concept_auc = (
        float(roc_auc_score(concept_y, concept_p)) if len(np.unique(concept_y)) == 2 else None
    )
    result.update(
        brier_increase=increase,
        control_brier=float(np.mean((control_y - control_p) ** 2)),
        concept_brier=float(np.mean((concept_y - concept_p) ** 2)),
        ci95=[float(low), float(high)],
        control_auc=control_auc,
        concept_auc=concept_auc,
        auc_drop=None if control_auc is None or concept_auc is None else control_auc - concept_auc,
        auc_drop_threshold=float(settings.get("auc_drop_threshold", 0.05)),
        control_prevalence=float(np.mean(control_y)),
        concept_prevalence=float(np.mean(concept_y)),
        label_count=len(control_y),
        conditional_change_evidence=bool(increase >= result["effect_threshold"] and low > 0),
    )
    return result


def _export_evidently(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    reference_p: np.ndarray,
    current_p: np.ndarray,
    threshold: float,
    output_dir: Path,
    config: dict,
) -> dict:
    """Importa a API 0.7 sob demanda e exporta apenas colunas necessárias ao relatório."""
    from evidently import DataDefinition, Dataset, Report
    from evidently.core.datasets import BinaryClassification
    from evidently.presets import ClassificationPreset, DataDriftPreset

    settings = config.get("monitoring", {})
    columns = [column for column in FEATURES if column in reference and column in current]
    numerical = [column for column in columns if column not in PAY_COLUMNS]
    categorical = [column for column in columns if column in PAY_COLUMNS]
    ref, cur = reference[columns].copy(), current[columns].copy()
    drift_preset = DataDriftPreset(
        columns=columns,
        num_method="ks",
        num_threshold=float(settings.get("ks_alpha", 0.05)),
        cat_method="psi",
        cat_threshold=float(settings.get("psi_threshold", 0.20)),
    )
    presets = [drift_preset]
    classification = None
    two_classes = all(
        _labels_available(frame) and frame["target"].nunique() == 2
        for frame in [reference, current]
    )
    if two_classes:
        for source, destination, probabilities in [
            (reference, ref, reference_p),
            (current, cur, current_p),
        ]:
            destination["target"] = source["target"].to_numpy()
            destination["probability"] = probabilities
            destination["prediction"] = (probabilities >= threshold).astype(int)
        classification = [
            BinaryClassification(
                target="target", prediction_probas="probability", prediction_labels="prediction"
            )
        ]
        presets.append(ClassificationPreset(probas_threshold=threshold))
    schema = DataDefinition(
        numerical_columns=numerical,
        categorical_columns=categorical,
        classification=classification,
    )
    snapshot = Report(presets).run(
        current_data=Dataset.from_pandas(cur, data_definition=schema),
        reference_data=Dataset.from_pandas(ref, data_definition=schema),
    )
    html_path = output_dir / "evidently.html"
    snapshot.save_html(str(html_path))
    banner = (
        '<aside role="note" id="politica-primaria" '
        'style="padding:20px;background:#fff3cd;color:#332701;border:2px solid #ad7a00">'
        "<strong>Decisão primária do projeto:</strong> consulte "
        '<a href="monitoring.json">monitoring.json</a> e o '
        '<a href="../index.html">resumo consolidado</a>. '
        "Este relatório Evidently é complementar: seus testes usam p-valores KS brutos, "
        "sem correção Benjamini-Hochberg (BH) nem exigência de efeito mínimo. "
        "A política primária exige KS com BH e D mínimo nos atributos contínuos e PSI nos "
        "estados de pagamento. A suavização do PSI e a regra agregada do Evidently também "
        "podem divergir. Drift de X ou do score não comprova mudança em P(Y|X)."
        "</aside>"
    )
    html = html_path.read_text(encoding="utf-8")
    html, insertions = re.subn(
        r"(<body\b[^>]*>)", lambda match: match[0] + banner, html, count=1, flags=re.I
    )
    if insertions != 1:
        raise RuntimeError(
            "O HTML complementar não possui estrutura esperada para o aviso da política."
        )
    html_path.write_text(html, encoding="utf-8")
    snapshot.save_json(str(output_dir / "evidently.json"))
    return {
        "html": "evidently.html",
        "json": "evidently.json",
        "classification_included": two_classes,
        "decision_role": "Relatório bruto complementar; a decisão primária está em drift.",
        "differences": (
            "Evidently usa KS por coluna sem BH nem efeito mínimo, PSI com suavização própria "
            "e regra agregada própria. Essas decisões não substituem a política do projeto."
        ),
    }


def evaluate_scenario(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    model,
    threshold: float,
    output_dir: Path,
    config: dict,
) -> dict:
    """Avalia o lote validado e persiste métricas agregadas e relatório Evidently real."""
    _require_disjoint_ids(reference, current)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # O predictor aplica o contrato antes de qualquer inferência.
    reference_p = _probabilities(predict(model, reference, threshold), len(reference))
    current_p = _probabilities(predict(model, current, threshold), len(current))
    labels_status = (
        current.attrs.get("simulation", {}).get("labels_status", "available_labels")
        if _labels_available(current)
        else "pending_labels"
    )
    result = {
        "status": "pending_report",
        "performance": _performance(current, current_p, threshold),
        "reference_performance": _performance(reference, reference_p, threshold),
        "drift": compute_drift(reference, current, config),
        "labels_status": labels_status,
        "label_count": int(current["target"].notna().sum()) if "target" in current else 0,
        "label_coverage": (
            float(current["target"].notna().mean()) if "target" in current and len(current) else 0.0
        ),
        "label_delay": "Não observado; cenários acadêmicos contrafactuais.",
        "concept_status": "pending_labels"
        if labels_status == "pending_labels"
        else "requires_pair",
        "evidently_html": "evidently.html",
        "aggregate_json": "monitoring.json",
        "simulation": dict(current.attrs.get("simulation", {})),
        "prediction_monitoring": _prediction_monitoring(
            reference, current, reference_p, current_p, threshold, config
        ),
        "evidently": {
            "status": "pending",
            "decision_role": "Relatório bruto complementar; a decisão primária está em drift.",
            "differences": (
                "Testes KS brutos sem BH nem efeito mínimo; PSI e regra agregada próprios. "
                "O relatório não substitui a política primária do projeto."
            ),
        },
    }
    aggregate_path = output_dir / "monitoring.json"
    _write_aggregate(aggregate_path, result)
    try:
        report = _export_evidently(
            reference, current, reference_p, current_p, threshold, output_dir, config
        )
    except Exception as error:
        # A mensagem da dependência pode incluir dados; persiste somente o nome do tipo.
        result["status"] = "failed"
        result["evidently"].update(status="failed", error_type=type(error).__name__)
        _write_aggregate(aggregate_path, result)
        raise
    result["evidently"].update(report, status="success")
    result["status"] = "success"
    _write_aggregate(aggregate_path, result)
    return result
