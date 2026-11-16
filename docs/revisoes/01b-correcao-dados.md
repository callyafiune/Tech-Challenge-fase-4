# Revisão adversarial — 01b-correcao-dados

Modelo solicitado: `fable`. Modelo retornado: `claude-fable-5-2`.

# Revisão adversarial: `credito_monitorado` (config, contrato, dados, baseline), 2ª passagem

**Escopo e limites.** Leitura estática dos oito arquivos colados; nada foi executado. Ficam sem prova:

- **Hashes fixados:** não confirmei `DATASET_ZIP_SHA256` nem `DATASET_XLS_SHA256`; o comentário "verificado em 16/11/2026" é só uma alegação.
- **Dados reais:** nenhum teste lê o XLS oficial, então não há evidência de que ele passe em `validate_batch`. De memória, os domínios da UCI cabem no contrato.
- **Fora do pacote:** `pipeline.py`, `drift.py`, `monitoring.py`, `tracking.py`, `fairness.py`, docs, enunciado, `pyproject.toml`/`uv.lock` e o roteiro. Aderência ao enunciado e o uso real da configuração não são julgáveis aqui.

Conferi à mão que `params.yaml` passa em `load_config`, que os valores esperados em `test_metricas_com_valores_conhecidos...` estão corretos e que o split dá 15000/4500/4500/6000 (30.000 linhas) e 200/60/60/80 (400 linhas).

## Críticos

Nenhum defeito crítico demonstrável. Não há vazamento treino/validação no código:

- **Partições:** disjuntas por `record_id`, com cobertura total verificada.
- **Ajuste:** `fit` só no treino, `early_stopping=False`, nenhuma transformação ajustada fora do pipeline.
- **Entrada do modelo:** restrita a `FEATURES`; nenhuma variável é posterior ao alvo.

## Importantes

1. **`data.py::load_dataset` engole o próprio erro de integridade, e a verificação não tem teste negativo.**
   - Defeito: o `raise ValueError("A integridade...")` está dentro do `try` que captura `(OSError, ValueError)`, então sai como "Não foi possível ler o dataset XLS oficial."
   - Reprodução: chamar `load_dataset` com qualquer arquivo de hash diferente.
   - Impacto: adulteração fica indistinguível de erro de E/S, e remover a comparação de hash não quebraria nenhum teste.
   - Correção: comparar o hash fora do `try` e adicionar teste com `match=` para hash divergente.

2. **O caminho real de leitura do XLS nunca é exercitado.**
   - Defeito: `test_load_dataset_normaliza_cabecalho...` substitui o pin e `pd.read_excel`. `header=1`, `engine="xlrd"`, os nomes reais das colunas e o contrato sobre dados reais ficam sem cobertura.
   - Correção: teste de integração marcado (pulado sem cache) que rode `acquire_dataset`, `load_dataset` e `split_dataset` no arquivo oficial e afirme 30.000 linhas e a prevalência esperada.

3. **Os testes de `load_config` são só negativos e podem passar por vacuidade.**
   - Defeito: nenhum teste afirma que `load_config(params.yaml)` tem sucesso. Se o YAML padrão ficar inválido (por exemplo, chave nova sem atualizar `allowed`), todos os `pytest.raises(ConfigError)` continuam verdes.
   - Correção: teste positivo e `match=` com o nome do parâmetro nos negativos.

4. **Continua sem partição de teste intocada e sem origem do limiar e dos hiperparâmetros.**
   - Defeito: a única estimativa de `train_baseline` é na validação. "Sem ajuste na validação" é docstring, não prova.
   - Impacto: se `threshold: 0.30` ou `150/0.08/15` foram escolhidos olhando essa partição, as métricas são otimistas.
   - Correção: reportar a métrica final em partição nunca usada para decisão e registrar como os valores foram escolhidos.

5. **`contracts.py`: `age` continua tratada de forma inconsistente.**
   - Defeito: `age` é demográfica e está em `FEATURES`. O teste `test_rotulo_id_e_demograficos_nao_influenciam_probabilidade` não altera `age`, então o nome afirma mais do que o modelo garante. `REQUIRED_COLUMNS` ainda lista os demográficos, contradizendo o schema, que os tornou opcionais na inferência.
   - Correção: justificar ou remover `age`, renomear o teste e corrigir ou apagar `REQUIRED_COLUMNS`.

6. **Defaults silenciosos permitem ignorar a configuração sem falha.**
   - Defeito: `load_dataset(min_rows=5000)`, `split_dataset(seed=42)`, `config.get("seed", 42)` e `evaluate_model(threshold=0.30)` repetem valores do YAML.
   - Impacto: o pacote não mostra que `dataset.min_rows` e `seed` chegam a essas funções; se o chamador omitir, nada acusa.
   - Correção: tornar os argumentos obrigatórios e usar `config["seed"]`.

7. **Lacunas restantes em `acquire_dataset`.**
   - Sem teste: manifesto adulterado ou inválido, falha de rede, download com hash divergente (e cache não gravado), ZIP com zero ou dois `.xls`, `BadZipFile`.
   - Sem teste: o conteúdo de `attrs["provenance"]`.

## Menores

- **`config.py::_number`:** um inteiro YAML com mais de ~308 dígitos faz `math.isfinite` lançar `OverflowError`, que escapa de `load_config`. Compare os limites antes ou capture a exceção.
- **`load_config`, valores degenerados:** aceita `threshold` 0 ou 1, `auc_drop_threshold` 0, `ks_min_effect` 0 e `psi_epsilon` até quase 1.
- **`acquire_dataset`, escrita:** os três arquivos são regravados a cada chamada, sem atomicidade. Uma interrupção corrompe um cache antes válido, sem autorrecuperação nem orientação na mensagem. Grave só quando ausente, via arquivo temporário e `os.replace`.
- **`acquire_dataset`, erros crus:** `read(50_000_001)` nunca é checado. `http.client.IncompleteRead` e um `UnicodeDecodeError` do manifesto escapam sem tratamento.
- **`acquire_dataset`, manifesto:** `source_rows: 30000` é fixo, não medido. `retrieved_at_utc` fica incorreto se o manifesto for recriado a partir do cache.
- **`load_dataset`, leituras:** o hash é calculado sobre bytes lidos, mas `read_excel` reabre o arquivo e `stat()` roda fora do `try`. Use `io.BytesIO(content)` e `len(content)`.
- **`load_dataset`, proveniência:** `DataFrame.attrs` é experimental e sua propagação pelo split não é garantida. Devolva a proveniência de forma explícita.
- **`validate_batch`:** a mensagem única não informa coluna nem regra, que não são dados pessoais. O `except` com `TypeError`/`ValueError` mascara bugs como violação de contrato.
- **`split_dataset`:** as frações `0.3` e `3/7` dependem de arredondamento; no caso de 400 linhas a margem é da ordem de 1 ULP. Use contagens inteiras.
- **`model.py`:** o `DummyClassifier(prior)` com limiar 0,30 tem F1, recall e precisão iguais a 0 por construção, e o ganho de AUC é sempre AUC − 0,5. Faltam intervalo de confiança e análise de calibração.
- **Testes:** vários `pytest.raises(ValueError)` sem `match` (e `DataContractError` é `ValueError`). Não há valor fracionário para `education`/`marriage` nem teste de que o `fit` ignora os rótulos da validação.
- **Linhas duplicadas da UCI:** registros idênticos exceto pelo ID podem cair em partições diferentes; não é tratado nem documentado.
- **`docs/revisoes/01-dados-modelo.md`:** descreve o código anterior às correções (por exemplo, `predict` exigindo demográficos). Marque como histórico ou anexe o status das ressalvas.
- **`params.yaml`, a conferir nos módulos ausentes:** KS com `alpha` 0,05 em 20 features sem correção visível de multiplicidade; KS em variáveis discretas (`pay_*`, `age`); `concept_flip_probability: 0.8`, que torna a detecção trivial.

## Ressalvas da revisão anterior

| Item anterior | Situação no pacote |
|---|---|
| 1. Proveniência em `load_dataset` | Parcial: hash comparado, mas erro engolido e sem teste negativo |
| 2. Validação de configuração | Resolvido no código; uso pelo chamador não demonstrado |
| 3. Partição de teste e origem do limiar | Não resolvido |
| 4. `age` e demográficos | Parcial: demográficos opcionais, `age` e nome do teste inalterados |
| 5. Cobertura | Parcial: ver itens 2, 3 e 7 |
| `__context__`, `age` 30.5, caminho pandera, chaves desconhecidas | Resolvidos |

## Veredito

- **Conformidade:** não atestável para o desafio como um todo, porque enunciado, drift, monitoramento, tracking, docs e roteiro estão fora do pacote. No recorte, é parcial: a aquisição com integridade fixada, o contrato, o split e o baseline estão coerentes, mas não há prova de execução sobre dados reais.
- **Qualidade:** boa e melhor que na passagem anterior, sem vazamento identificado. As correções de proveniência e de configuração não estão protegidas por testes que falhariam se fossem removidas.
- **Resultado:** aprovado com ressalvas. Corrigir os itens 1, 2 e 3 e documentar os itens 4 e 5 antes da entrega.
