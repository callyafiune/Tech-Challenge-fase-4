"""Cenários contrafactuais e política estatística com resultados agregados."""

import hashlib

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from credito_monitorado.contracts import FEATURES, PAY_COLUMNS


def benjamini_hochberg(pvalues) -> np.ndarray:
    """Corrige uma família de p-valores, preservando sua ordem original."""
    values = np.asarray(pvalues, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("A família de p-valores deve ser finita e pertencer a [0, 1].")
    if not len(values):
        return values.copy()
    order = np.argsort(values, kind="stable")
    ranked = values[order] * len(values) / np.arange(1, len(values) + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1].clip(0, 1)
    result = np.empty_like(values)
    result[order] = adjusted
    return result


def _numeric(values) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not len(array) or not np.isfinite(array).all():
        raise ValueError("A comparação exige vetores numéricos não vazios e finitos.")
    return array


def _require_disjoint_ids(reference: pd.DataFrame, current: pd.DataFrame) -> None:
    """Impede que a referência holdout seja reutilizada como observação de produção."""
    if "record_id" not in reference or "record_id" not in current:
        raise ValueError("A comparação operacional exige identificadores em ambos os lotes.")
    if not set(reference["record_id"]).isdisjoint(current["record_id"]):
        raise ValueError("Referência e produção não podem ter sobreposição de identificadores.")


def population_stability_index(
    reference, current, *, categorical=False, epsilon=1e-6, bins=10
) -> float:
    """Calcula PSI com suporte compartilhado e intervalos fixados somente pela referência."""
    ref, cur = _numeric(reference), _numeric(current)
    if not np.isfinite(epsilon) or epsilon <= 0 or bins < 2:
        raise ValueError("Epsilon deve ser positivo e a quantidade de intervalos deve ser >= 2.")
    if categorical:
        categories = np.union1d(ref, cur)
        ref_counts = np.array([(ref == category).sum() for category in categories])
        cur_counts = np.array([(cur == category).sum() for category in categories])
    else:
        if np.ptp(ref) == 0:
            # Isola a massa constante e distingue desvios para ambos os lados.
            value = ref[0]
            edges = np.array([-np.inf, value, np.nextafter(value, np.inf), np.inf])
        else:
            internal = np.unique(np.quantile(ref, np.arange(1, bins) / bins))
            edges = np.concatenate(([-np.inf], internal, [np.inf]))
        ref_counts = np.histogram(ref, bins=edges)[0]
        cur_counts = np.histogram(cur, bins=edges)[0]
    ref_share = ref_counts / len(ref) + epsilon
    cur_share = cur_counts / len(cur) + epsilon
    ref_share /= ref_share.sum()
    cur_share /= cur_share.sum()
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def build_scenarios(
    production_pool: pd.DataFrame, reference: pd.DataFrame, config: dict
) -> dict[str, pd.DataFrame]:
    """Amostra por X e aplica inversões sintéticas, sem reposição dentro dos lotes."""
    settings = config.get("simulation", {})
    size = int(settings.get("batch_size", 2500))
    seed = int(config.get("seed", 42))
    _require_disjoint_ids(reference, production_pool)
    if size <= 0 or len(production_pool) < size:
        raise ValueError("O pool deve comportar o lote positivo solicitado sem reposição.")
    if not production_pool["record_id"].is_unique:
        raise ValueError("O pool exige identificadores únicos.")
    median = float(np.median(_numeric(reference["limit_bal"])))
    weights = np.ones(len(production_pool))
    weights[production_pool["limit_bal"].to_numpy() <= median] *= settings.get(
        "low_limit_weight", 3.0
    )
    weights[production_pool["pay_0"].to_numpy() >= 1] *= settings.get("late_payment_weight", 4.0)
    if not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("Os pesos de seleção devem ser positivos e finitos.")
    probability = float(settings.get("concept_flip_probability", 0.8))
    if not 0 <= probability <= 1:
        raise ValueError("A probabilidade de inversão deve pertencer a [0, 1].")
    scenarios = {}
    for name, offset, selection_weights in [("control", 0, None), ("covariate", 1, weights)]:
        probabilities = None if selection_weights is None else weights / weights.sum()
        positions = np.random.default_rng(seed + offset).choice(
            len(production_pool), size=size, replace=False, p=probabilities
        )
        frame = production_pool.iloc[positions].copy().reset_index(drop=True)
        frame.attrs["simulation"] = {
            "scenario": name,
            "selection_seed": seed + offset,
            "selection": "uniforme" if probabilities is None else "ponderada_somente_por_X",
            "labels_status": "original_labels" if "target" in frame else "pending_labels",
            "counterfactual": True,
            "rows": size,
        }
        scenarios[name] = frame
    flip_seed = seed + 2
    for name, source in [("concept", "control"), ("combined", "covariate")]:
        frame = scenarios[source].copy(deep=True)
        metadata = dict(frame.attrs["simulation"])
        metadata.update(
            scenario=name,
            paired_with=source,
            flip_seed=flip_seed,
            flip_assignment="SHA-256 estável de seed e record_id; compartilhado entre cenários",
        )
        if "target" in frame:
            eligible = frame["pay_0"].to_numpy() <= 0
            # A seleção/ordenação do lote não muda a intervenção atribuída à mesma pessoa.
            uniform = np.fromiter(
                (
                    int.from_bytes(
                        hashlib.sha256(f"{flip_seed}:{int(record_id)}".encode("ascii")).digest()[
                            :8
                        ],
                        "big",
                    )
                    / 2**64
                    for record_id in frame["record_id"]
                ),
                dtype=float,
                count=size,
            )
            mask = eligible & (uniform < probability)
            frame.loc[mask, "target"] = 1 - frame.loc[mask, "target"]
            metadata.update(
                labels_status="counterfactual_simulated",
                eligible_rows=int(eligible.sum()),
                flipped_rows=int(mask.sum()),
                flip_probability=probability,
            )
        frame.attrs["simulation"] = metadata
        scenarios[name] = frame
    return scenarios


def compute_drift(reference: pd.DataFrame, current: pd.DataFrame, config: dict) -> dict:
    """Aplica KS com BH/efeito às contínuas e PSI aos estados de pagamento."""
    settings = config.get("monitoring", {})
    alpha = float(settings.get("ks_alpha", 0.05))
    effect = float(settings.get("ks_min_effect", 0.10))
    psi_threshold = float(settings.get("psi_threshold", 0.20))
    epsilon = float(settings.get("psi_epsilon", 1e-6))
    columns = [column for column in FEATURES if column in reference]
    if not columns or any(column not in current for column in columns):
        raise ValueError("Os lotes devem compartilhar os atributos monitorados da referência.")
    sufficient = min(len(reference), len(current)) >= int(settings.get("min_rows", 200))
    results = {}
    continuous = []
    for column in columns:
        categorical = column in PAY_COLUMNS
        result = {
            "method": "psi" if categorical else "ks_bh_effect",
            "score": None,
            "psi": None,
            "ks": None,
            "pvalue": None,
            "pvalue_adjusted": None,
            "threshold": psi_threshold if categorical else alpha,
            "min_effect": None if categorical else effect,
            "drift": None,
        }
        if sufficient:
            ref, cur = _numeric(reference[column]), _numeric(current[column])
            psi = population_stability_index(ref, cur, categorical=categorical, epsilon=epsilon)
            result["psi"] = psi
            if categorical:
                result.update(score=psi, drift=bool(psi >= psi_threshold))
            else:
                statistic = ks_2samp(ref, cur)
                result.update(
                    score=float(statistic.statistic),
                    ks=float(statistic.statistic),
                    pvalue=float(statistic.pvalue),
                )
                continuous.append(column)
        results[column] = result
    adjusted = benjamini_hochberg([results[column]["pvalue"] for column in continuous])
    for column, pvalue in zip(continuous, adjusted, strict=True):
        results[column]["pvalue_adjusted"] = float(pvalue)
        results[column]["drift"] = bool(pvalue <= alpha and results[column]["ks"] >= effect)
    drifted = [column for column, result in results.items() if result["drift"]]
    return {
        "features": results,
        "summary": {
            "status": "ok" if sufficient else "insufficient_sample",
            "reference_rows": len(reference),
            "current_rows": len(current),
            "min_rows": int(settings.get("min_rows", 200)),
            "drift_detected": bool(drifted) if sufficient else None,
            "drifted_features": drifted,
            "n_features": len(columns),
            "drift_share": len(drifted) / len(columns) if sufficient else None,
            "rules": {
                "continuous": "p ajustado BH <= alpha e KS D >= efeito mínimo",
                "categorical": "PSI >= limiar; suporte é a união das categorias observadas",
                "bh_family": continuous,
                "continuous_psi": "Complementar; quantis da referência com extremos abertos",
                "interpretation": "Drift de X não comprova alteração em P(Y|X).",
            },
        },
    }
