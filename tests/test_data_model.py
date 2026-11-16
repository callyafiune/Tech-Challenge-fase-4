"""Separação sem vazamento e predições do modelo sobre dados sintéticos."""

import hashlib
import io
from itertools import combinations
from pathlib import Path
from zipfile import ZipFile

import joblib
import numpy as np
import pandas as pd
import pytest
import yaml

from credito_monitorado import data
from credito_monitorado.config import ConfigError, load_config
from credito_monitorado.data import acquire_dataset, load_dataset, split_dataset
from credito_monitorado.model import evaluate_model, predict, train_baseline


@pytest.fixture
def base_sintetica():
    """Cria exemplos balanceados com sinal previsível e identificadores únicos."""
    quantidade = 400
    gerador = np.random.default_rng(17)
    rotulos = np.tile([0, 1], quantidade // 2)
    dados = {
        "record_id": np.arange(1, quantidade + 1),
        "limit_bal": gerador.uniform(10000, 300000, quantidade),
        "sex": gerador.integers(1, 3, quantidade),
        "education": gerador.integers(0, 7, quantidade),
        "marriage": gerador.integers(0, 4, quantidade),
        "age": gerador.integers(19, 80, quantidade),
        "target": rotulos,
    }
    for coluna in ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"]:
        dados[coluna] = rotulos * 3
    for mes in range(1, 7):
        dados[f"bill_amt{mes}"] = gerador.uniform(0, 100000, quantidade)
        dados[f"pay_amt{mes}"] = gerador.uniform(0, 10000, quantidade)
    return pd.DataFrame(dados)


@pytest.fixture
def modelo_treinado(base_sintetica):
    partes = split_dataset(base_sintetica, seed=42)
    configuracao = {
        "seed": 42,
        "model": {
            "max_iter": 20,
            "learning_rate": 0.1,
            "max_leaf_nodes": 7,
            "threshold": 0.3,
        },
    }
    resultado = train_baseline(partes["train"], partes["validation"], configuracao)
    return resultado, partes["production_pool"]


def test_particoes_sao_exclusivas_com_cobertura_total_e_proporcoes(base_sintetica):
    partes = split_dataset(base_sintetica, seed=42)
    assert set(partes) == {"train", "validation", "reference", "production_pool"}
    assert {nome: len(lote) for nome, lote in partes.items()} == {
        "train": 200,
        "validation": 60,
        "reference": 60,
        "production_pool": 80,
    }
    conjuntos = [set(lote["record_id"]) for lote in partes.values()]
    for primeiro, segundo in combinations(conjuntos, 2):
        assert primeiro.isdisjoint(segundo)
    assert set.union(*conjuntos) == set(base_sintetica["record_id"])
    for lote in partes.values():
        assert lote["target"].value_counts().to_dict() == {0: len(lote) // 2, 1: len(lote) // 2}


def test_seed_reproduz_particoes_e_outra_seed_muda_selecao(base_sintetica):
    primeira = split_dataset(base_sintetica, seed=42)
    repetida = split_dataset(base_sintetica, seed=42)
    diferente = split_dataset(base_sintetica, seed=99)
    for nome in primeira:
        pd.testing.assert_frame_equal(primeira[nome], repetida[nome])
    assert set(primeira["train"]["record_id"]) != set(diferente["train"]["record_id"])


def test_treino_retorna_metricas_e_limiar_configurado(modelo_treinado):
    resultado, _ = modelo_treinado
    assert resultado.threshold == pytest.approx(0.3)
    assert resultado.metrics
    assert resultado.pipeline is not None
    assert resultado.metrics["roc_auc"] > 0.95
    assert resultado.metrics["dummy_roc_auc"] == pytest.approx(0.5)


def test_predict_sem_rotulo_preserva_ids_e_aplica_limiar(modelo_treinado):
    resultado, lote = modelo_treinado
    entrada = lote.drop(columns="target").iloc[::-1]
    saida = predict(resultado.pipeline, entrada, resultado.threshold)
    assert list(saida.columns) == ["record_id", "probability", "prediction"]
    assert saida["record_id"].tolist() == entrada["record_id"].tolist()
    assert np.isfinite(saida["probability"]).all()
    assert saida["probability"].between(0, 1).all()
    np.testing.assert_array_equal(saida["prediction"], (saida["probability"] >= 0.3).astype(int))
    assert saida["prediction"].nunique() == 2


def test_rotulo_id_e_demograficos_excluidos_nao_influenciam_probabilidade(modelo_treinado):
    resultado, lote = modelo_treinado
    original = predict(resultado.pipeline, lote, resultado.threshold)
    alterado = lote.copy()
    alterado["target"] = 1 - alterado["target"]
    alterado["record_id"] += 10000
    alterado["sex"] = 3 - alterado["sex"]
    alterado["education"] = (alterado["education"] + 1) % 7
    alterado["marriage"] = (alterado["marriage"] + 1) % 4
    nova = predict(resultado.pipeline, alterado, resultado.threshold)
    np.testing.assert_allclose(nova["probability"], original["probability"], rtol=0, atol=0)


def test_limiar_altera_decisao_sem_alterar_probabilidade(modelo_treinado):
    resultado, lote = modelo_treinado
    baixo = predict(resultado.pipeline, lote.drop(columns="target"), 0.0)
    alto = predict(resultado.pipeline, lote.drop(columns="target"), 1.0)
    np.testing.assert_array_equal(baixo["probability"], alto["probability"])
    assert baixo["prediction"].eq(1).all()
    assert alto["prediction"].eq(0).all()


def test_pipeline_persistida_reproduz_predicoes(modelo_treinado, tmp_path):
    resultado, lote = modelo_treinado
    caminho = tmp_path / "modelo.joblib"
    joblib.dump(resultado.pipeline, caminho)
    restaurado = joblib.load(caminho)
    esperado = predict(resultado.pipeline, lote, resultado.threshold)
    obtido = predict(restaurado, lote, resultado.threshold)
    pd.testing.assert_frame_equal(obtido, esperado)


@pytest.fixture
def cache_sintetico(tmp_path, monkeypatch):
    """Substitui somente pins e transporte para testar integridade sem rede."""
    xls = b"conteudo sintetico apenas para teste do cache"
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as arquivo:
        arquivo.writestr("default.xls", xls)
    zip_bytes = buffer.getvalue()
    monkeypatch.setattr(data, "DATASET_ZIP_SHA256", hashlib.sha256(zip_bytes).hexdigest())
    monkeypatch.setattr(data, "DATASET_XLS_SHA256", hashlib.sha256(xls).hexdigest())
    monkeypatch.setattr(data, "urlopen", lambda *args, **kwargs: io.BytesIO(zip_bytes))
    caminho = acquire_dataset(tmp_path)

    def rede_proibida(*args, **kwargs):
        raise AssertionError("O cache disponível não deve acionar a rede.")

    monkeypatch.setattr(data, "urlopen", rede_proibida)
    return tmp_path, caminho, xls


def test_cache_integro_e_reutilizado_sem_rede(cache_sintetico):
    diretorio, caminho, conteudo = cache_sintetico
    assert acquire_dataset(diretorio) == caminho
    assert caminho.read_bytes() == conteudo


@pytest.mark.parametrize("arquivo", ["uci350.zip", "default_of_credit_card_clients.xls"])
def test_cache_corrompido_bloqueia_aquisicao(cache_sintetico, arquivo):
    diretorio, _, _ = cache_sintetico
    (diretorio / arquivo).write_bytes(b"arquivo alterado")
    with pytest.raises(ValueError):
        acquire_dataset(diretorio)


@pytest.mark.parametrize(
    ("secao", "campo", "valor"),
    [
        ("model", "threshold", 1.1),
        ("simulation", "batch_size", 200.5),
        ("monitoring", "ks_alpha", float("nan")),
        ("monitoring", "bootstrap_samples", True),
        ("dataset", "min_rows", 4999),
        ("monitoring", "psi_epsilon", 0),
        ("monitoring", "psi_epsilon", 1),
        ("monitoring", "psi_epsilon", -0.01),
        ("monitoring", "psi_epsilon", float("nan")),
        ("monitoring", "psi_epsilon", True),
        ("monitoring", "brier_increase_threshold", 0),
        ("monitoring", "brier_increase_threshold", 1.01),
    ],
)
def test_config_rejeita_parametros_invalidos(tmp_path, secao, campo, valor):
    caminho_padrao = Path(__file__).resolve().parents[1] / "params.yaml"
    config = yaml.safe_load(caminho_padrao.read_text(encoding="utf-8"))
    config[secao][campo] = valor
    caminho = tmp_path / "config.yaml"
    caminho.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(caminho)


def test_config_rejeita_monitoramento_com_amostra_maior_que_lote(tmp_path):
    caminho_padrao = Path(__file__).resolve().parents[1] / "params.yaml"
    config = yaml.safe_load(caminho_padrao.read_text(encoding="utf-8"))
    config["simulation"]["batch_size"] = 200
    config["monitoring"]["min_rows"] = 201
    caminho = tmp_path / "config.yaml"
    caminho.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(caminho)


def test_metricas_com_valores_conhecidos_e_limiar_inclusivo():
    metricas = evaluate_model([0, 0, 1, 1], [0.1, 0.4, 0.3, 0.9], threshold=0.3)
    assert metricas["roc_auc"] == pytest.approx(0.75)
    assert metricas["average_precision"] == pytest.approx(5 / 6)
    assert metricas["brier_score"] == pytest.approx(0.1675)
    assert metricas["precision"] == pytest.approx(2 / 3)
    assert metricas["recall"] == pytest.approx(1.0)
    assert metricas["f1"] == pytest.approx(0.8)
    assert metricas["accuracy"] == pytest.approx(0.75)


@pytest.mark.parametrize(
    ("rotulos", "probabilidades", "limiar"),
    [
        ([1, 1], [0.1, 0.9], 0.3),
        ([0, 2], [0.1, 0.9], 0.3),
        ([0, 1], [0.1], 0.3),
        ([0, 1], [0.1, np.nan], 0.3),
        ([0, 1], [0.1, np.inf], 0.3),
        ([0, 1], [0.1, 1.01], 0.3),
        ([0, 1], [0.1, 0.9], -0.1),
        ([], [], 0.3),
    ],
)
def test_metricas_rejeitam_entradas_invalidas(rotulos, probabilidades, limiar):
    with pytest.raises(ValueError):
        evaluate_model(rotulos, probabilidades, limiar)


@pytest.mark.parametrize("problema", ["ids_sobrepostos", "treino_classe_unica"])
def test_treino_bloqueia_vazamento_e_ausencia_de_classes(base_sintetica, problema):
    treino = base_sintetica.iloc[:200].copy()
    validacao = base_sintetica.iloc[200:].copy()
    if problema == "ids_sobrepostos":
        validacao.loc[validacao.index[0], "record_id"] = treino.iloc[0]["record_id"]
    else:
        treino["target"] = 0
    with pytest.raises(ValueError):
        train_baseline(treino, validacao, {"model": {}})


def test_inferencia_sem_demograficos_reproduz_probabilidades(modelo_treinado):
    resultado, lote = modelo_treinado
    reduzido = lote.drop(columns=["target", "sex", "education", "marriage"])
    completo = predict(resultado.pipeline, lote, resultado.threshold)
    minimo = predict(resultado.pipeline, reduzido, resultado.threshold)
    pd.testing.assert_frame_equal(completo, minimo)


@pytest.mark.parametrize("secao", [None, "model", "monitoring"])
def test_config_rejeita_chave_desconhecida_para_evitar_parametro_ignorado(tmp_path, secao):
    caminho_padrao = Path(__file__).resolve().parents[1] / "params.yaml"
    config = yaml.safe_load(caminho_padrao.read_text(encoding="utf-8"))
    destino = config if secao is None else config[secao]
    destino["parametro_digitado_errado"] = 1
    caminho = tmp_path / "config.yaml"
    caminho.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(caminho)


def test_load_dataset_normaliza_cabecalho_e_aplica_minimo_configurado(
    base_sintetica, tmp_path, monkeypatch
):
    """Isola a leitura XLS; normalização, contrato e contagem são reais."""
    base = pd.concat([base_sintetica] * 13, ignore_index=True).iloc[:5000].copy()
    base["record_id"] = np.arange(1, 5001)
    bruto = base.rename(columns={"record_id": "ID", "target": "default payment next month"})
    bruto.columns = [coluna.upper() for coluna in bruto.columns]
    conteudo = b"fixture da camada de leitura XLS"
    caminho = tmp_path / "fonte.xls"
    caminho.write_bytes(conteudo)
    monkeypatch.setattr(data, "DATASET_XLS_SHA256", hashlib.sha256(conteudo).hexdigest())
    monkeypatch.setattr(data.pd, "read_excel", lambda *args, **kwargs: bruto.copy())
    normalizado = load_dataset(caminho, min_rows=5000)
    pd.testing.assert_frame_equal(normalizado, base)
    with pytest.raises(ValueError):
        load_dataset(caminho, min_rows=6000)
    for minimo_invalido in [True, 4999, 5000.5]:
        with pytest.raises(ValueError):
            load_dataset(caminho, min_rows=minimo_invalido)


def test_configuracao_padrao_valida_e_preserva_limiares():
    caminho = Path(__file__).resolve().parents[1] / "params.yaml"
    config = load_config(caminho)
    assert config["model"]["threshold"] == pytest.approx(0.3)
    assert config["monitoring"]["ks_alpha"] == pytest.approx(0.05)
    assert config["monitoring"]["psi_threshold"] == pytest.approx(0.2)
    assert config["simulation"]["batch_size"] == 2500


def test_load_dataset_rejeita_pin_xls_divergente_antes_da_leitura(tmp_path, monkeypatch):
    caminho = tmp_path / "alterado.xls"
    caminho.write_bytes(b"XLS alterado")

    def leitura_proibida(*args, **kwargs):
        raise AssertionError("A integridade deve ser verificada antes de interpretar o XLS.")

    monkeypatch.setattr(data.pd, "read_excel", leitura_proibida)
    with pytest.raises(ValueError, match="integridade"):
        load_dataset(caminho)
