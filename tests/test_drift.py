"""Cenários controlados e estatísticas resistentes a casos degenerados."""

import numpy as np
import pandas as pd
import pytest

from credito_monitorado.drift import (
    benjamini_hochberg,
    build_scenarios,
    compute_drift,
    population_stability_index,
)


def criar_base(quantidade=1000):
    """Gera perfis sintéticos com suporte suficiente para seleção por X."""
    gerador = np.random.default_rng(91)
    atraso = np.resize([-2, -1, 0, 1, 2], quantidade)
    dados = {
        "record_id": np.arange(1, quantidade + 1),
        "limit_bal": np.linspace(10000.0, 500000.0, quantidade),
        "age": gerador.integers(19, 80, quantidade),
        "sex": np.ones(quantidade, dtype=int),
        "education": np.ones(quantidade, dtype=int),
        "marriage": np.ones(quantidade, dtype=int),
        "target": (atraso > 0).astype(int),
    }
    for coluna in ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"]:
        dados[coluna] = atraso
    for mes in range(1, 7):
        dados[f"bill_amt{mes}"] = gerador.uniform(0, 100000, quantidade)
        dados[f"pay_amt{mes}"] = gerador.uniform(0, 5000, quantidade)
    return pd.DataFrame(dados)


def configuracao():
    """Limiares da demonstração, reduzindo somente o tamanho do lote."""
    return {
        "seed": 42,
        "simulation": {
            "batch_size": 200,
            "low_limit_weight": 3.0,
            "late_payment_weight": 4.0,
            "concept_flip_probability": 0.8,
        },
        "monitoring": {
            "psi_threshold": 0.2,
            "ks_alpha": 0.05,
            "ks_min_effect": 0.1,
            "auc_drop_threshold": 0.05,
            "bootstrap_samples": 500,
            "min_rows": 200,
        },
    }


def referencia_independente(quantidade=1000):
    """Preserva a distribuição da fixture com identidades fora do pool."""
    return criar_base(quantidade).assign(record_id=lambda base: base["record_id"] + 100000)


def test_cenarios_tem_tamanho_ids_unicos_e_conceito_preserva_x():
    pool = criar_base()
    cenarios = build_scenarios(pool, referencia_independente(), configuracao())
    assert set(cenarios) == {"control", "covariate", "concept", "combined"}
    for lote in cenarios.values():
        assert len(lote) == 200
        assert lote["record_id"].is_unique
        assert set(lote["record_id"]).issubset(set(pool["record_id"]))
    controle, conceito = cenarios["control"], cenarios["concept"]
    pd.testing.assert_frame_equal(controle.drop(columns="target"), conceito.drop(columns="target"))
    alterados = controle["target"].to_numpy() != conceito["target"].to_numpy()
    assert alterados.any()
    assert (controle.loc[alterados, "pay_0"] <= 0).all()


def test_selecao_covariavel_independe_de_rotulos_e_nao_muda_perfis():
    pool = criar_base()
    invertido = pool.assign(target=1 - pool["target"])
    referencia = referencia_independente()
    original = build_scenarios(pool, referencia, configuracao())["covariate"]
    outro = build_scenarios(invertido, referencia, configuracao())["covariate"]
    pd.testing.assert_frame_equal(original.drop(columns="target"), outro.drop(columns="target"))
    esperado = pool.set_index("record_id").loc[original["record_id"]].reset_index()
    pd.testing.assert_frame_equal(original.reset_index(drop=True), esperado[original.columns])


def test_drift_forte_em_duas_features_e_controle_identico_estavel():
    referencia = criar_base()
    atual = referencia.assign(limit_bal=1500000.0, pay_0=8)
    resultado = compute_drift(referencia, atual, configuracao())
    assert resultado["features"]["limit_bal"]["drift"]
    assert resultado["features"]["pay_0"]["drift"]
    assert resultado["summary"]["drift_detected"]
    controle = compute_drift(referencia, referencia.copy(), configuracao())
    assert not controle["summary"]["drift_detected"]


def test_psi_constante_finito_e_mudanca_constante_detectada():
    iguais = population_stability_index(np.ones(200), np.ones(200))
    distintos = population_stability_index(np.ones(200), np.full(200, 2.0))
    assert iguais == pytest.approx(0.0)
    assert np.isfinite(distintos)
    assert distintos >= 0.2


def test_psi_categoria_nova_e_simetrico_com_suporte_compartilhado():
    referencia = np.zeros(200, dtype=int)
    atual = np.full(200, 8, dtype=int)
    psi = population_stability_index(referencia, atual, categorical=True)
    inverso = population_stability_index(atual, referencia, categorical=True)
    assert np.isfinite(psi)
    assert psi >= 0.2
    assert psi == pytest.approx(inverso)


def test_bh_corrige_multiplicidade_preservando_ordem_original():
    corrigidos = benjamini_hochberg([0.04, 0.001, 0.03, 0.2])
    np.testing.assert_allclose(corrigidos, [0.05333333333333334, 0.004, 0.05333333333333334, 0.2])


def test_mesmo_cliente_recebe_mesma_intervencao_em_conceito_e_combinado():
    pool = criar_base()
    cenarios = build_scenarios(pool, referencia_independente(), configuracao())
    conceito = cenarios["concept"].set_index("record_id")
    combinado = cenarios["combined"].set_index("record_id")
    comuns = conceito.index.intersection(combinado.index)
    assert len(comuns) > 0
    pd.testing.assert_series_equal(conceito.loc[comuns, "target"], combinado.loc[comuns, "target"])


def test_cenarios_rejeitam_referencia_com_ids_do_pool():
    pool = criar_base()
    with pytest.raises(ValueError):
        build_scenarios(pool, pool.iloc[:200], configuracao())


@pytest.mark.parametrize("seed", [7, 42, 99])
def test_cadeia_cenario_detector_detecta_selecao_e_preserva_controle(seed):
    pool = criar_base(20000)
    referencia = referencia_independente(5000)
    config = configuracao()
    config["seed"] = seed
    config["simulation"]["batch_size"] = 2500
    cenarios = build_scenarios(pool, referencia, config)
    assert len(cenarios["control"]) != len(referencia)
    assert not cenarios["control"]["limit_bal"].equals(referencia["limit_bal"])
    covariavel = compute_drift(referencia, cenarios["covariate"], config)
    controle = compute_drift(referencia, cenarios["control"], config)
    assert {"limit_bal", "pay_0"}.issubset(covariavel["summary"]["drifted_features"])
    assert not controle["summary"]["drift_detected"]


@pytest.mark.integracao
def test_cadeia_real_uci_com_cache_local_e_configuracao_padrao():
    from pathlib import Path

    from credito_monitorado.config import load_config
    from credito_monitorado.data import load_dataset, split_dataset

    raiz = Path(__file__).resolve().parents[1]
    caminho = raiz / "data/raw/default_of_credit_card_clients.xls"
    if not caminho.exists():
        pytest.skip("Cache UCI ausente; integração real não usa rede nem baixa dados.")
    config = load_config(raiz / "params.yaml")
    partes = split_dataset(load_dataset(caminho), seed=config["seed"])
    assert {nome: len(lote) for nome, lote in partes.items()} == {
        "train": 15000,
        "validation": 4500,
        "reference": 4500,
        "production_pool": 6000,
    }
    for lote in partes.values():
        assert set(lote["target"].unique()) == {0, 1}
    referencia = partes["reference"]
    cenarios = build_scenarios(partes["production_pool"], referencia, config)
    covariavel = compute_drift(referencia, cenarios["covariate"], config)
    controle = compute_drift(referencia, cenarios["control"], config)
    assert {"limit_bal", "pay_0"}.issubset(covariavel["summary"]["drifted_features"])
    assert not controle["summary"]["drift_detected"]
