"""Carregamento e validação explícita dos parâmetros de execução."""

import math
from pathlib import Path

import yaml

from credito_monitorado.data import DATASET_URL


class ConfigError(ValueError):
    """Configuração ausente ou fora dos limites operacionais permitidos."""


def _number(value: object, minimum: float, maximum: float, integer: bool = False) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and minimum <= value <= maximum
        and math.isfinite(value)
        and (not integer or isinstance(value, int))
    )


def load_config(path: Path) -> dict:
    """Lê YAML sem execução de objetos e rejeita limites incoerentes."""
    try:
        config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        raise ConfigError("Não foi possível ler a configuração YAML.") from None
    if not isinstance(config, dict):
        raise ConfigError("A configuração deve conter um mapeamento de parâmetros.")
    limits = {
        "seed": (0, 2**32 - 1, True),
        "dataset.min_rows": (5000, 30000, True),
        "model.max_iter": (1, 2000, True),
        "model.learning_rate": (0.000001, 1, False),
        "model.max_leaf_nodes": (2, 255, True),
        "model.threshold": (0, 1, False),
        "simulation.batch_size": (200, 6000, True),
        "simulation.low_limit_weight": (0.000001, 100, False),
        "simulation.late_payment_weight": (0.000001, 100, False),
        "simulation.concept_flip_probability": (0, 1, False),
        "monitoring.psi_threshold": (0.000001, 10, False),
        "monitoring.psi_epsilon": (math.nextafter(0, 1), math.nextafter(1, 0), False),
        "monitoring.ks_alpha": (0.000001, 0.999999, False),
        "monitoring.ks_min_effect": (0, 1, False),
        "monitoring.auc_drop_threshold": (0, 1, False),
        "monitoring.brier_increase_threshold": (math.nextafter(0, 1), 1, False),
        "monitoring.bootstrap_samples": (100, 10000, True),
        "monitoring.min_rows": (20, 6000, True),
        "monitoring.max_stage_seconds": (1, 86400, False),
        "monitoring.max_rss_mb": (64, 65536, False),
    }
    allowed = {
        "dataset": {"url", "min_rows"},
        "model": {"max_iter", "learning_rate", "max_leaf_nodes", "threshold"},
        "simulation": {
            "batch_size",
            "low_limit_weight",
            "late_payment_weight",
            "concept_flip_probability",
        },
        "monitoring": {name.split(".")[1] for name in limits if name.startswith("monitoring.")},
        "tracking": {"experiment_name"},
    }
    if set(config) != {"seed", *allowed}:
        raise ConfigError("A configuração contém seções ausentes ou desconhecidas.")
    for section, keys in allowed.items():
        if not isinstance(config[section], dict) or set(config[section]) != keys:
            raise ConfigError("A configuração contém parâmetros ausentes ou desconhecidos.")
    try:
        for name, bounds in limits.items():
            value = config
            for part in name.split("."):
                value = value[part]
            if not _number(value, *bounds):
                raise ConfigError(f"Parâmetro fora dos limites permitidos: {name}.")
        if config["dataset"]["url"] != DATASET_URL:
            raise ConfigError("A origem do dataset deve ser a fonte UCI aprovada.")
        if (
            not isinstance(config["tracking"]["experiment_name"], str)
            or not config["tracking"]["experiment_name"].strip()
        ):
            raise ConfigError("O nome do experimento deve ser um texto não vazio.")
        if config["monitoring"]["min_rows"] > config["simulation"]["batch_size"]:
            raise ConfigError("O tamanho do lote deve atender ao mínimo de monitoramento.")
    except (KeyError, TypeError):
        raise ConfigError("A configuração está incompleta ou possui estrutura inválida.") from None
    return config
