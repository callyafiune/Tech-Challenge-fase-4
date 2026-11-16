# Revisão adversarial — 01-dados-modelo

Modelo solicitado: `fable`. Modelo retornado: `claude-fable-5-2`.

# Revisão adversarial: pacote `credito_monitorado` (config, contrato, dados, baseline)

**Escopo e limites.** Analisei só os sete arquivos colados, por leitura estática; nada foi executado. Três pontos ficam sem prova:

- **Hash do dataset:** não confirmei `DATASET_ZIP_SHA256`. O comentário "verificado em 16/11/2026" é uma alegação.
- **Dataset real contra o contrato:** não há evidência de que o XLS real passe em `validate_batch`. Pelo que conheço dos domínios da UCI deveria passar, mas isso não está demonstrado.
- **Módulos ausentes:** simulação de drift, monitoramento (PSI/KS/bootstrap), tracking, scripts, docs, `pyproject.toml`/`uv.lock` e o roteiro não estão no pacote. O enunciado do Tech Challenge também não, então a aderência só pode ser julgada pelo que o código sugere.

## Críticos

Nenhum defeito crítico demonstrável nos arquivos fornecidos. Não encontrei vazamento treino/validação no código:

- **Partições:** são disjuntas por `record_id`, com cobertura total verificada.
- **Ajuste:** o `fit` usa só o treino e o pipeline não tem transformações ajustadas fora dele.
- **Alvo e demográficos:** `ColumnTransformer` restringe a entrada a `FEATURES`.

## Importantes

1. **`data.py::load_dataset` atesta proveniência sem verificá-la.**
   - Defeito: qualquer XLS que passe no contrato recebe `attrs["provenance"]` com `source_url` da UCI e `synthetic: False`. O hash é calculado, mas não é comparado com nada.
   - Impacto: um arquivo sintético ou adulterado sai carimbado como real, e essa evidência pode ir para tracking ou relatório.
   - Correção: comparar com `xls_sha256` do manifesto ou com um hash fixado do XLS, e falhar se divergir.

2. **`config.py::load_config` valida parâmetros incompletos e parâmetros mortos.**
   - Defeito: `monitoring.psi_epsilon` e `monitoring.brier_increase_threshold` estão em `params.yaml` e não são validados. Já `dataset.min_rows` e `dataset.url` são validados e não são consumidos: `load_dataset` fixa `5000` e `data.py` usa sua própria `DATASET_URL`, duplicada como literal.
   - Impacto: ausência ou valor inválido só aparece em runtime, e alterar `dataset.min_rows` não tem efeito.
   - Correção: incluir os dois parâmetros em `limits`, passar `min_rows` a `load_dataset` e importar a URL de um único lugar.

3. **Não há partição de teste intocada, e a origem do limiar e dos hiperparâmetros não está documentada.**
   - Defeito: as partições são treino, validação, referência e pool de produção. A única estimativa reportada por `train_baseline` é na validação.
   - Impacto: se `threshold: 0.30` ou `max_iter`/`learning_rate`/`max_leaf_nodes` foram escolhidos olhando essa validação, a métrica é otimista. O docstring "sem ajuste na validação" não é verificável.
   - Correção: reportar a métrica final em `reference` (se nunca usada para decisão) ou criar uma partição de teste, e registrar como o 0.30 foi escolhido.

4. **`contracts.py`: tratamento inconsistente de atributos sensíveis.**
   - Defeito: `sex`, `education` e `marriage` ficam fora de `FEATURES`, mas `age` entra. O teste `test_rotulo_id_e_demograficos_nao_influenciam_probabilidade` afirma mais do que o modelo garante. Além disso, `predict` exige os três demográficos na inferência sem usá-los.
   - Impacto: a alegação de neutralidade demográfica é parcial, e a exigência viola minimização de dados se não houver uso em análise de equidade.
   - Correção: justificar `age` ou removê-la, renomear o teste e tornar os demográficos opcionais em `require_target=False`.

5. **Lacunas de cobertura.**
   - Sem teste: `load_config`, `acquire_dataset` (hash divergente, cache adulterado, manifesto inválido), `load_dataset` e `evaluate_model` (valores conhecidos, classe única, entradas inválidas).
   - Sem teste em `train_baseline`: rejeição de IDs sobrepostos e de treino com uma só classe.
   - Assert fraco: `test_treino_retorna_metricas_e_limiar_configurado` só verifica que `metrics` não é vazio. Em dados perfeitamente separáveis deveria exigir `roc_auc ≈ 1` e `dummy_roc_auc == 0.5`.

## Menores

- **`acquire_dataset`, cache:** as escritas não são atômicas. Um ZIP parcial falha no hash para sempre, sem autorrecuperação nem orientação na mensagem. Os três arquivos são regravados a cada chamada.
- **`acquire_dataset`, download:** o limite `read(50_000_001)` nunca é checado. `http.client.IncompleteRead` não é `OSError` e escapa cru.
- **`acquire_dataset`, manifesto:** `retrieved_at_utc` recebe a hora atual mesmo quando o ZIP veio do cache, e `source_rows: 30000` é fixo, não medido.
- **`load_dataset`:** `xlrd.XLRDError` não é capturado e o arquivo é lido duas vezes (parse e hash).
- **`split_dataset`:** as frações `0.3` e `3/7` dependem de arredondamento de ponto flutuante. Conferi à mão que dão 15000/4500/4500/6000 para 30.000 linhas e 200/60/60/80 para 400. Para outros tamanhos pode haver desvio de uma linha; prefira contagens inteiras.
- **`validate_batch`, privacidade residual:** `raise ... from None` oculta o traceback, mas `__context__` ainda aponta para o `SchemaErrors` do pandera, com `failure_cases` e os dados. Levante a exceção fora do bloco `except`.
- **`validate_batch`, operabilidade:** a mensagem única não informa coluna nem regra violada, que não são dados pessoais. O `except ValueError` amplo também mascara bugs como violação de contrato.
- **`test_nao_trunca_numeros_fracionarios_para_inteiros`:** para `age`, `sex` e `target`, o valor 1.5 já cai no domínio. Só `record_id` e `pay_0` exercitam a checagem de inteiro. Use 30.5 para `age`.
- **`test_erro_e_logs_nao_expoem...`:** a rejeição ocorre na checagem de dtype, então o caminho do pandera, onde os valores existiriam, não é exercitado.
- **`model.py`, defaults duplicados:** `config.get("seed", 42)` e `threshold=0.30` em `evaluate_model` repetem a configuração em silêncio.
- **`model.py`, comparador fraco:** `roc_auc_gain_over_dummy` é sempre `AUC − 0,5`. Com prevalência próxima de 22% e limiar 0,30, o dummy tem F1 e recall iguais a 0 por construção. Uma regressão logística seria um comparador mais informativo.
- **`model.py`, incerteza:** as métricas são pontuais, sem intervalo de confiança.
- **`load_config`:** aceita `threshold` 0 ou 1 e `auc_drop_threshold` 0, que são degenerados, e ignora chaves desconhecidas.
- **Linhas duplicadas:** pelo que me lembro, a base UCI tem algumas dezenas de linhas idênticas exceto pelo ID. Elas podem cair em treino e validação; o efeito é desprezível, mas não é tratado nem documentado.

## Veredito

- **Conformidade:** não atestável para o desafio como um todo, porque drift, monitoramento, tracking, documentação e roteiro estão fora do pacote. No recorte entregue (dados reais com integridade fixada, contrato, split estratificado, baseline), a conformidade é parcial com ressalvas: itens 1 a 3 e a execução não comprovada.
- **Qualidade:** boa no recorte, com código defensivo e sem vazamento identificado. Fica abaixo do que a documentação interna afirma em proveniência, validação de configuração e cobertura de testes.
- **Resultado:** aprovado com ressalvas. Corrigir os itens 1, 2 e 5 antes da entrega.
