"""Auditoria descritiva agregada com supressão de grupos pequenos."""

import numpy as np
from sklearn.metrics import roc_auc_score

from credito_monitorado.contracts import validate_batch


def audit_groups(df, probabilities, threshold: float, min_group_size: int = 30) -> dict:
    """Resume aprovação e erros na referência; não conclui ausência ou causa de viés."""
    frame = validate_batch(df)
    probability = np.asarray(probabilities, dtype=float)
    if (
        probability.shape != (len(frame),)
        or not np.isfinite(probability).all()
        or ((probability < 0) | (probability > 1)).any()
        or not np.isfinite(threshold)
        or not 0 <= threshold <= 1
        or not isinstance(min_group_size, int)
        or isinstance(min_group_size, bool)
        or min_group_size < 30
    ):
        raise ValueError("Parâmetros inválidos para auditoria agregada de grupos.")
    target = frame["target"].to_numpy()
    prediction = probability >= threshold
    masks = {
        "sex": {
            "codigo_1": frame["sex"].to_numpy() == 1,
            "codigo_2": frame["sex"].to_numpy() == 2,
        },
        "age": {
            "19_29": frame["age"].between(19, 29).to_numpy(),
            "30_49": frame["age"].between(30, 49).to_numpy(),
            "50_mais": (frame["age"].to_numpy() >= 50),
        },
    }
    groups = {}
    gaps = {}
    for dimension, dimension_masks in masks.items():
        results = {}
        complementary = any(
            0 < int(mask.sum()) < min_group_size for mask in dimension_masks.values()
        )
        for name, mask in dimension_masks.items():
            rows = int(mask.sum())
            item = {"rows": rows, "status": "suppressed" if rows < min_group_size else "ok"}
            if complementary and rows >= min_group_size:
                item["status"] = "suppressed_complementary"
            if item["status"] == "ok":
                y, decision, p = target[mask], prediction[mask], probability[mask]
                positive, negative = y == 1, y == 0
                item.update(
                    approval_rate=float((~decision).mean()),
                    default_rate=float(y.mean()),
                    tpr=float(decision[positive].mean())
                    if positive.sum() >= min_group_size
                    else None,
                    fpr=float(decision[negative].mean())
                    if negative.sum() >= min_group_size
                    else None,
                    roc_auc=float(roc_auc_score(y, p))
                    if positive.any() and negative.any()
                    else None,
                )
            results[name] = item
        groups[dimension] = results
        rates = [group["approval_rate"] for group in results.values() if group["status"] == "ok"]
        gaps[dimension] = max(rates) - min(rates) if len(rates) >= 2 else None
    return {
        "population": "reference",
        "rows": len(frame),
        "threshold": threshold,
        "minimum_group_size": min_group_size,
        "suppression_policy": (
            "Grupo não vazio abaixo do mínimo suprime taxas de toda a dimensão. "
            "TPR e FPR exigem denominador específico de pelo menos 30 observações."
        ),
        "groups": groups,
        "approval_rate_gaps": gaps,
        "interpretation": (
            "Diferenças descritivas na referência; não são estimativas causais "
            "ou prova de discriminação. "
            "Amostragem, composição, dados de Taiwan/2005 e proxies limitam generalização. "
            "Excluir atributos demográficos do modelo não garante ausência de viés. "
            "Taxas e métricas de grupos pequenos são suprimidas; AUROC requer ambas as classes."
        ),
    }
