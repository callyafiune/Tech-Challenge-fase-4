"""Evidências supervisionadas pareadas e artefatos reais do Evidently."""

import json

import numpy as np
import pytest
from test_drift import configuracao, criar_base

from credito_monitorado import monitoring
from credito_monitorado.model import train_baseline
from credito_monitorado.monitoring import compare_concept, evaluate_scenario


def test_comparacao_pareada_detecta_piora_com_x_e_predicoes_invariantes():
    controle = criar_base(200)
    conceito = controle.copy()
    conceito.loc[conceito["pay_0"] <= 0, "target"] = 1
    probabilidades = np.where(controle["target"] == 1, 0.9, 0.1)
    resultado = compare_concept(
        controle, conceito, probabilidades, probabilidades.copy(), configuracao()
    )
    assert resultado["same_features"]
    assert resultado["same_predictions"]
    assert resultado["brier_increase"] == pytest.approx(0.48)
    assert resultado["ci95"][0] > 0
    assert resultado["conditional_change_evidence"]


def test_controle_sem_degradacao_nao_produz_evidencia_de_conceito():
    controle = criar_base(200)
    probabilidades = np.where(controle["target"] == 1, 0.9, 0.1)
    resultado = compare_concept(
        controle, controle.copy(), probabilidades, probabilidades.copy(), configuracao()
    )
    assert resultado["brier_increase"] == pytest.approx(0.0)
    assert not resultado["conditional_change_evidence"]


def test_ausencia_rotulos_fica_pendente_sem_fabricar_evidencia():
    controle = criar_base(200)
    probabilidades = np.full(200, 0.3)
    resultado = compare_concept(
        controle,
        controle.drop(columns="target"),
        probabilidades,
        probabilidades.copy(),
        configuracao(),
    )
    assert resultado["status"] == "pending_labels"
    assert not resultado["conditional_change_evidence"]
    assert resultado.get("brier_increase") is None


@pytest.mark.parametrize("alteracao", ["atributo", "identificador", "probabilidade"])
def test_pares_nao_comparaveis_nao_autorizam_evidencia_de_conceito(alteracao):
    controle = criar_base(200)
    conceito = controle.assign(target=1 - controle["target"])
    probabilidades = np.where(controle["target"] == 1, 0.9, 0.1)
    novas_probabilidades = probabilidades.copy()
    if alteracao == "atributo":
        conceito.loc[0, "limit_bal"] += 100.0
    elif alteracao == "identificador":
        conceito.loc[0, "record_id"] += 10000
    else:
        novas_probabilidades[0] += 0.01
    resultado = compare_concept(
        controle, conceito, probabilidades, novas_probabilidades, configuracao()
    )
    assert not resultado["conditional_change_evidence"]
    assert resultado.get("brier_increase") is None
    assert not (resultado["same_features"] and resultado["same_predictions"])


@pytest.fixture
def lotes_monitorados():
    """Partições exclusivas com distribuições semelhantes, sem ordenação por limite."""
    base = criar_base().sample(frac=1, random_state=47).reset_index(drop=True)
    config = configuracao()
    config["model"] = {
        "max_iter": 10,
        "learning_rate": 0.1,
        "max_leaf_nodes": 7,
        "threshold": 0.3,
    }
    treinado = train_baseline(base.iloc[:400], base.iloc[400:600], config)
    return base.iloc[600:800].copy(), base.iloc[800:].copy(), treinado.pipeline, config


@pytest.mark.integracao
def test_evidently_gera_html_e_json_com_numeros_recuperaveis(tmp_path, lotes_monitorados):
    referencia, atual, modelo, config = lotes_monitorados
    resultado = evaluate_scenario(referencia, atual, modelo, 0.3, tmp_path, config)
    html = (tmp_path / "evidently.html").read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "limit_bal" in html
    assert "Decisão primária" in html
    assert "BH" in html
    assert "efeito" in html.lower()
    evidentemente = json.loads((tmp_path / "evidently.json").read_text(encoding="utf-8"))
    assert isinstance(evidentemente, dict)
    assert evidentemente
    resumo = json.loads((tmp_path / "monitoring.json").read_text(encoding="utf-8"))
    assert isinstance(resumo["drift"]["features"]["limit_bal"]["score"], (int, float))
    assert resumo["performance"]
    assert resultado["performance"] == resumo["performance"]


def test_monitoramento_rejeita_sobreposicao_antes_de_inferir(
    tmp_path, lotes_monitorados, monkeypatch
):
    referencia, _, modelo, config = lotes_monitorados

    def inferencia_proibida(*args, **kwargs):
        raise AssertionError("Sobreposição deve ser bloqueada antes da inferência.")

    monkeypatch.setattr(monitoring, "predict", inferencia_proibida)
    with pytest.raises(ValueError):
        evaluate_scenario(referencia, referencia.copy(), modelo, 0.3, tmp_path, config)


def test_rotulos_pendentes_preservam_monitoramento_de_score_e_taxa(
    tmp_path, lotes_monitorados, monkeypatch
):
    referencia, atual, modelo, config = lotes_monitorados
    monkeypatch.setattr(monitoring, "_export_evidently", lambda *args, **kwargs: {})
    resultado = evaluate_scenario(
        referencia, atual.drop(columns="target"), modelo, 0.3, tmp_path, config
    )
    assert resultado["labels_status"] == "pending_labels"
    assert resultado["performance"] is None
    saude = resultado["prediction_monitoring"]
    for campo in ["reference_positive_rate", "current_positive_rate"]:
        assert 0 <= saude[campo] <= 1
    for campo in ["psi", "ks", "pvalue"]:
        assert np.isfinite(saude["score"][campo])
    assert saude["current_prevalence"] is None


def test_falha_evidently_preserva_json_primario_e_erro_seguro(
    tmp_path, lotes_monitorados, monkeypatch
):
    referencia, atual, modelo, config = lotes_monitorados
    segredo = "CLIENTE_CONFIDENCIAL_987654321"

    def exportacao_indisponivel(*args, **kwargs):
        parcial = json.loads((tmp_path / "monitoring.json").read_text(encoding="utf-8"))
        assert parcial["drift"]["features"]
        assert parcial["evidently"]["status"] == "pending"
        raise RuntimeError(segredo)

    monkeypatch.setattr(monitoring, "_export_evidently", exportacao_indisponivel)
    with pytest.raises(RuntimeError, match=segredo):
        evaluate_scenario(referencia, atual, modelo, 0.3, tmp_path, config)
    conteudo = (tmp_path / "monitoring.json").read_text(encoding="utf-8")
    resumo = json.loads(conteudo)
    assert resumo["drift"]["features"]
    assert resumo["status"] == "failed"
    assert resumo["evidently"]["status"] == "failed"
    assert resumo["evidently"]["error_type"] == "RuntimeError"
    assert segredo not in conteudo
