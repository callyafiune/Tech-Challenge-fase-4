"""Baseline de risco e métricas; o alvo positivo representa inadimplência."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

from credito_monitorado.contracts import FEATURES, validate_batch


@dataclass
class TrainingResult:
    """Artefato treinado e avaliação na validação mantida fora do ajuste."""

    pipeline: Pipeline
    threshold: float
    metrics: dict[str, float]


def evaluate_model(y_true, probabilities, threshold: float = 0.30) -> dict[str, float]:
    """Calcula métricas agregadas; AUROC exige ambas as classes no lote."""
    labels = np.asarray(y_true)
    probabilities = np.asarray(probabilities, dtype=float)
    if (
        labels.ndim != 1
        or probabilities.ndim != 1
        or len(labels) != len(probabilities)
        or len(labels) == 0
        or not np.isin(labels, [0, 1]).all()
        or not np.isfinite(probabilities).all()
        or ((probabilities < 0) | (probabilities > 1)).any()
        or not np.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("Entradas inválidas para avaliação agregada do modelo.")
    if len(np.unique(labels)) != 2:
        raise ValueError("A avaliação AUROC exige as duas classes do alvo.")
    decisions = (probabilities >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "f1": float(f1_score(labels, decisions, zero_division=0)),
        "recall": float(recall_score(labels, decisions, zero_division=0)),
        "precision": float(precision_score(labels, decisions, zero_division=0)),
        "accuracy": float(accuracy_score(labels, decisions)),
        "brier_score": float(brier_score_loss(labels, probabilities)),
    }


performance_metrics = evaluate_model


def predict(pipeline: Pipeline, df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Valida antes de inferir e preserva a ordem e a identidade das entradas."""
    validated = validate_batch(df, require_target=False)
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("O limiar de decisão deve pertencer ao intervalo de zero a um.")
    probabilities = pipeline.predict_proba(validated[FEATURES])[:, 1]
    return pd.DataFrame(
        {
            "record_id": validated["record_id"].to_numpy(),
            "probability": probabilities,
            "prediction": (probabilities >= threshold).astype(int),
        }
    )


def train_baseline(train: pd.DataFrame, validation: pd.DataFrame, config: dict) -> TrainingResult:
    """Ajusta somente no treino; limiar vem da configuração, sem ajuste na validação."""
    train = validate_batch(train)
    validation = validate_batch(validation)
    if not set(train["record_id"]).isdisjoint(validation["record_id"]):
        raise ValueError("Treino e validação devem conter identidades exclusivas.")
    if set(train["target"].unique()) != {0, 1}:
        raise ValueError("O treino exige as duas classes do alvo.")
    params = config["model"]
    threshold = float(params["threshold"])
    pipeline = Pipeline(
        [
            ("features", ColumnTransformer([("financeiras", "passthrough", FEATURES)])),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    max_iter=params["max_iter"],
                    learning_rate=params["learning_rate"],
                    max_leaf_nodes=params["max_leaf_nodes"],
                    random_state=config.get("seed", 42),
                    early_stopping=False,
                ),
            ),
        ]
    )
    pipeline.fit(train[FEATURES], train["target"])
    scored = predict(pipeline, validation, threshold)
    metrics = evaluate_model(validation["target"], scored["probability"], threshold)
    dummy = DummyClassifier(strategy="prior").fit(train[FEATURES], train["target"])
    dummy_metrics = evaluate_model(
        validation["target"], dummy.predict_proba(validation[FEATURES])[:, 1], threshold
    )
    metrics.update({f"dummy_{name}": value for name, value in dummy_metrics.items()})
    metrics["roc_auc_gain_over_dummy"] = metrics["roc_auc"] - metrics["dummy_roc_auc"]
    return TrainingResult(pipeline=pipeline, threshold=threshold, metrics=metrics)
