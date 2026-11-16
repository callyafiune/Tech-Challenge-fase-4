"""Auditoria agregada com métricas conhecidas e supressão de grupos pequenos."""

import json

import numpy as np
import pytest
from test_drift import criar_base

from credito_monitorado.fairness import audit_groups


def test_taxas_gaps_e_supressao_de_grupo_menor_que_trinta():
    base = criar_base(120)
    base["sex"] = np.repeat([1, 2], 60)
    base["age"] = [25] * 29 + [40] * 91
    base["target"] = np.tile(np.repeat([1, 0], 30), 2)
    probabilidades = np.concatenate([np.repeat([0.9, 0.1], 30), np.full(60, 0.1)])
    auditoria = audit_groups(base, probabilidades, 0.3)
    primeiro = auditoria["groups"]["sex"]["codigo_1"]
    segundo = auditoria["groups"]["sex"]["codigo_2"]
    assert primeiro["approval_rate"] == pytest.approx(0.5)
    assert primeiro["default_rate"] == pytest.approx(0.5)
    assert primeiro["tpr"] == pytest.approx(1.0)
    assert primeiro["fpr"] == pytest.approx(0.0)
    assert primeiro["roc_auc"] == pytest.approx(1.0)
    assert segundo["approval_rate"] == pytest.approx(1.0)
    assert segundo["tpr"] == pytest.approx(0.0)
    assert segundo["roc_auc"] == pytest.approx(0.5)
    assert auditoria["approval_rate_gaps"]["sex"] == pytest.approx(0.5)
    suprimido = auditoria["groups"]["age"]["19_29"]
    assert suprimido["rows"] == 29
    assert suprimido["status"] == "suppressed"
    assert not {"approval_rate", "default_rate", "tpr", "fpr", "roc_auc"}.intersection(suprimido)
    complementar = auditoria["groups"]["age"]["30_49"]
    assert complementar["rows"] == 91
    assert not {"approval_rate", "default_rate", "tpr", "fpr", "roc_auc"}.intersection(complementar)
    assert "record_id" not in json.dumps(auditoria)


def test_grupo_com_classe_unica_nao_inventa_auc_ou_tpr():
    base = criar_base(60).assign(target=0, sex=1)
    grupo = audit_groups(base, np.full(60, 0.1), 0.3)["groups"]["sex"]["codigo_1"]
    assert grupo["roc_auc"] is None
    assert grupo["tpr"] is None
    assert grupo["fpr"] == pytest.approx(0.0)


@pytest.mark.parametrize("positivos", [29, 31])
def test_taxas_condicionais_suprimem_denominador_menor_que_trinta(positivos):
    base = criar_base(60).assign(sex=1)
    base["target"] = [1] * positivos + [0] * (60 - positivos)
    grupo = audit_groups(base, np.full(60, 0.1), 0.3)["groups"]["sex"]["codigo_1"]
    assert grupo["approval_rate"] == pytest.approx(1.0)
    if positivos < 30:
        assert grupo["tpr"] is None
        assert grupo["fpr"] == pytest.approx(0.0)
    else:
        assert grupo["fpr"] is None
        assert grupo["tpr"] == pytest.approx(0.0)


@pytest.mark.parametrize("problema", ["comprimento", "nan", "infinito", "negativo", "acima_um"])
def test_auditoria_rejeita_probabilidades_invalidas(problema):
    probabilidades = np.full(60, 0.1)
    if problema == "comprimento":
        probabilidades = probabilidades[:-1]
    else:
        probabilidades[0] = {
            "nan": np.nan,
            "infinito": np.inf,
            "negativo": -0.01,
            "acima_um": 1.01,
        }[problema]
    with pytest.raises(ValueError):
        audit_groups(criar_base(60), probabilidades, 0.3)
