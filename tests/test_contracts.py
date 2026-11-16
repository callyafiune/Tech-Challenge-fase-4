"""Garantias do contrato de entrada e da proteção de dados nos erros."""

import numpy as np
import pandas as pd
import pytest

from credito_monitorado.contracts import DataContractError, validate_batch


@pytest.fixture
def lote_valido():
    """Lote mínimo com tipos e domínios válidos, sem dados reais."""
    dados = {
        "record_id": [11, 12, 13, 14],
        "limit_bal": [10000.0, 20000.0, 30000.0, 40000.0],
        "sex": [1, 2, 1, 2],
        "education": [0, 1, 2, 6],
        "marriage": [0, 1, 2, 3],
        "age": [19, 35, 65, 100],
        "target": [0, 1, 0, 1],
    }
    for coluna in ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"]:
        dados[coluna] = [-2, -1, 0, 8]
    for mes in range(1, 7):
        dados[f"bill_amt{mes}"] = [-1000000.0, 0.0, 12000.0, 2000000.0]
        dados[f"pay_amt{mes}"] = [0.0, 500.0, 1000.0, 2000000.0]
    return pd.DataFrame(dados)


def test_aceita_lote_valido_preservando_dados(lote_valido):
    original = lote_valido.copy(deep=True)
    resultado = validate_batch(lote_valido)
    pd.testing.assert_frame_equal(resultado, original)
    pd.testing.assert_frame_equal(lote_valido, original)


def test_inferencia_aceita_ausencia_do_rotulo(lote_valido):
    entrada = lote_valido.drop(columns="target")
    pd.testing.assert_frame_equal(validate_batch(entrada, require_target=False), entrada)


@pytest.mark.parametrize("coluna", ["target", "age", "pay_amt6", "sex"])
def test_rejeita_coluna_obrigatoria_ausente(lote_valido, coluna):
    with pytest.raises(DataContractError):
        validate_batch(lote_valido.drop(columns=coluna))


def test_inferencia_valida_rotulo_quando_presente(lote_valido):
    lote_valido.loc[0, "target"] = 7
    with pytest.raises(DataContractError):
        validate_batch(lote_valido, require_target=False)


def test_rejeita_coluna_inesperada(lote_valido):
    lote_valido["informacao_extra"] = 1
    with pytest.raises(DataContractError):
        validate_batch(lote_valido)


def test_rejeita_lote_vazio(lote_valido):
    with pytest.raises(DataContractError):
        validate_batch(lote_valido.iloc[:0])


def test_rejeita_identificador_duplicado(lote_valido):
    lote_valido.loc[1, "record_id"] = lote_valido.loc[0, "record_id"]
    with pytest.raises(DataContractError):
        validate_batch(lote_valido)


@pytest.mark.parametrize("coluna", ["record_id", "limit_bal", "age", "pay_0", "target"])
def test_rejeita_nulos(lote_valido, coluna):
    lote_valido[coluna] = lote_valido[coluna].astype(float)
    lote_valido.loc[0, coluna] = np.nan
    with pytest.raises(DataContractError):
        validate_batch(lote_valido)


@pytest.mark.parametrize(
    ("coluna", "valor"),
    [
        ("limit_bal", 0.0),
        ("limit_bal", 2000000.01),
        ("limit_bal", np.inf),
        ("age", 18),
        ("age", 101),
        ("pay_0", -3),
        ("pay_6", 9),
        ("bill_amt1", -1000000.01),
        ("bill_amt6", 2000000.01),
        ("pay_amt1", -0.01),
        ("pay_amt6", 2000000.01),
        ("target", 2),
        ("sex", 0),
        ("education", 7),
        ("marriage", 4),
    ],
)
def test_rejeita_valores_fora_do_dominio(lote_valido, coluna, valor):
    lote_valido.loc[0, coluna] = valor
    with pytest.raises(DataContractError):
        validate_batch(lote_valido)


@pytest.mark.parametrize("coluna", ["record_id", "age", "pay_0", "target", "sex"])
def test_nao_trunca_numeros_fracionarios_para_inteiros(lote_valido, coluna):
    lote_valido[coluna] = lote_valido[coluna].astype(float)
    lote_valido.loc[0, coluna] = 1.5
    with pytest.raises(DataContractError):
        validate_batch(lote_valido)


def test_rejeita_texto_em_coluna_numerica(lote_valido):
    lote_valido["limit_bal"] = lote_valido["limit_bal"].astype(str)
    with pytest.raises(DataContractError):
        validate_batch(lote_valido)


def test_erro_e_logs_nao_expoem_identificador_ou_valor_invalido(lote_valido, caplog):
    identificador = 987654321
    segredo = "VALOR_INVALIDO_CONFIDENCIAL"
    lote_valido.loc[0, "record_id"] = identificador
    lote_valido["age"] = lote_valido["age"].astype(object)
    lote_valido.loc[0, "age"] = segredo
    with pytest.raises(DataContractError) as erro:
        validate_batch(lote_valido)
    mensagem = str(erro.value) + caplog.text
    assert segredo not in mensagem
    assert str(identificador) not in mensagem


def test_inferencia_aceita_ausencia_de_demograficos(lote_valido):
    entrada = lote_valido.drop(columns=["target", "sex", "education", "marriage"])
    pd.testing.assert_frame_equal(validate_batch(entrada, require_target=False), entrada)


def test_idade_fracionaria_dentro_do_intervalo_e_rejeitada(lote_valido):
    lote_valido["age"] = lote_valido["age"].astype(float)
    lote_valido.loc[0, "age"] = 30.5
    with pytest.raises(DataContractError):
        validate_batch(lote_valido)


def test_erro_financeiro_nao_encadeia_excecao_com_dados_individuais(lote_valido, caplog):
    lote_valido.loc[0, "limit_bal"] = 987654321.25
    lote_valido.loc[0, "record_id"] = 876543210
    with pytest.raises(DataContractError) as erro:
        validate_batch(lote_valido)
    assert erro.value.__context__ is None
    assert erro.value.__cause__ is None
    for sensivel in ["987654321.25", "876543210"]:
        assert sensivel not in str(erro.value) + caplog.text
