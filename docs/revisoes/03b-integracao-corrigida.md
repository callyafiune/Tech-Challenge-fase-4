# Revisão adversarial — 03b-integracao-corrigida

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

## Correções de observabilidade e integração

Revisão estática: não executei nada. As correções dos itens 1, 2, 3, 7 e 8 estão feitas em substância e a do item 4 está parcial, mas suficiente. Não encontrei defeito crítico de código. O que ainda impede a entrega está fora do código: o histórico de commits e a falta de registro de uma execução real completa.

## Verificação das correções

| Item | Estado | O que o código mostra | Resíduo |
|---|---|---|---|
| 1. `_contract_demo` | Corrigido | Controle positivo validado antes das violações; `limit_bal` já em float, então o NaN não muda o dtype; uma única mutação por variante. | A regra violada não é conferida: o isolamento vem da construção, porque `DataContractError` é genérico. `inference_calls` continua literal, agora declarado como tal. |
| 2. Proveniência | Corrigido | `_source_identity` grava `git_dirty`, hash por arquivo (incluindo `uv.lock`) e hash agregado; a chave `source` entra no manifesto. | Nenhum teste afirma `source` ou `git_dirty` no resumo. |
| 3. `_safe_tracking_uri` | Corrigido para os casos testados | Remove userinfo, query e fragmento em cinco esquemas. | Senha com `/` não codificada vaza inteira (menor 3). |
| 4. Alegações fixas | Parcial, aceitável | `_verify_partitions` falha em sobreposição e perda de cobertura, com teste; a tabela de partições deriva de `summary["partitions"]`. | `trained_only_on` e as frases do HTML continuam literais. São verdadeiras: `train_baseline` só ajusta em `train`. |
| 7. Auditoria de grupos | Corrigido | Seção no `index.html`, chave no manifesto e `auditoria_grupos.json` no MLflow; supressão complementar; TPR e FPR com denominador mínimo de 30. | A tabela HTML omite TPR, FPR, inadimplência e o gap, embora calculados. |
| 8. Caminho de falha | Corrigido | `stage` captura `BaseException`; `failed_stage` gravado; `falha.json` mínimo; persistência e sincronização dentro de estágios; exceção original preservada. | `failed_stage` pode apontar uma falha esperada (menor 2). |

## Evidência dos 130 testes

- **Contagem coerente:** contei os casos parametrizados dos sete arquivos de teste e o total é 130 (40 + 41 + 12 + 10 + 9 + 11 + 7). Bate com o registro, portanto não há testes fora do pacote.
- **Natureza do registro:** `docs/verificacao.json` é um resumo transcrito, não saída bruta. Não traz lista por teste, JUnit nem `source_sha256` ou commit que o ligue ao código revisado.
- **Arquivos fora do pacote:** o registro do `ruff format` fala em 40 arquivos e o pacote tem 20 `.py`. Existe Python que não revisei.

## Críticos

1. **Entrega: o histórico de commits não existe.**
   - O enunciado exige "histórico de commits semântico e organizado" em repositório GitHub. Na versão analisada, as fontes ainda não estavam vinculadas a commits semânticos.
   - Toda execução nesse estado grava `git_dirty: true` e um `HEAD` que não contém o código.
   - Correção: versionar as fontes em commits semânticos antes de gerar a execução de referência.

Não há defeito crítico de código.

## Importantes

1. **Não há registro de uma execução real completa.**
   - `test_pipeline_real...` troca a origem por dados sintéticos.
   - `test_cadeia_real_uci...` usa a base real, mas para em `compute_drift`.
   - Os números da entrega (PSI de `pay_0` = 0,2053, alertas, HTML) aparecem só como prosa em `tratamento.md`.
   - Correção: acrescentar a `verificacao.json` o comando `credito run`, o código de saída, o `execution_id`, o `source_sha256`, o hash do manifesto, os atributos em drift e os alertas por cenário.

## Menores

1. **Item 1, `test_demonstracao_bloqueia_lotes_invalidos...`:** continua tautológico, pois `_contract_demo` nunca chama `predict`. Correção: chamar `predict` com o lote combinado e um modelo espião, esperando `DataContractError` e zero chamadas a `predict_proba`.
2. **Item 8, `run_pipeline`:** `failures[-1]` inclui eventos com `expected_failure`. Uma falha fora de estágio após a demonstração (por exemplo, a escrita do alerta em `_contract_demo`) é atribuída a `contrato_invalido_combinado`. Correção: filtrar `expected_failure`.
3. **Item 3, `_safe_tracking_uri`:** em `postgresql://u:pa/ss@host/db`, o `urlsplit` corta o netloc em `u:pa`, não encontra `@` e publica a URI inteira. Correção: para esquemas não SQLite, publicar só esquema e host. `output_dir` absoluto também segue para `resumo.json` e para o MLflow.
4. **Cobertura do item 8:** nenhum teste afirma `failed_stage`, nem cobre falha depois de existir `run_id`. Nesse ponto o `resumo.json` em disco já diz "sucesso" e depende do handler para ser regravado. Correção: fazer `finalize_tracking` falhar e afirmar resumo "falha", estágio `sincronizacao_mlflow` e run `FAILED`.
5. **`tracking.py`, runs filhos:** o `evidently.html` aponta para `monitoring.json` e `../index.html`, que não existem no run filho.
6. **`check_health`:** roda antes de existirem os eventos de `finalizacao_artefatos` e `sincronizacao_mlflow`, que nunca são avaliados.
7. **`cli.py`:** continua sem teste.

## Novos achados em código não coberto pelas correções

- **`reporting.py::render_summary`:** `label_names` usa a chave `"original"`, mas `build_scenarios` emite `"original_labels"`. A coluna "Rótulos" mostra o texto cru nos cenários controle e covariável.
- **`drift.py::build_scenarios`:** `"counterfactual": True` também é gravado no controle, que é amostra uniforme com rótulos originais.
- **Margem de `pay_0`:** o requisito de duas variáveis depende de 0,2053 contra o limiar de 0,20, na seed fixada. Nenhum teste verifica o que o próprio Evidently marca: o PSI dele usa outra suavização e pode não acusar `pay_0`. Confira `covariate/evidently.json` na execução real antes de gravar o roteiro.
- **`test_evidently_gera_html...`:** "Decisão primária", "BH" e "efeito" vêm do banner injetado, não do Evidently.

## Não verificável neste pacote

- README (LGPD, base legal, retenção, vieses), `docs/causalidade.md` e `docs/roteiro_star.md`.
- A justificativa para a referência ser um holdout independente, já que o enunciado a descreve como "usada no treino".
- CI e `scripts/`.

## Veredito

- **Correções:** aprovadas. Os resíduos são menores e nenhum invalida as evidências.
- **Integração:** coerente por leitura estática: contrato na ingestão, partições disjuntas verificadas, treino só em `train`, limiar fixo, cenários só do pool, artefatos e MLflow sincronizados. Não encontrei vazamento treino/teste.
- **Conformidade:** o código das Etapas 1 a 3 adere ao enunciado. A entrega ainda não está conforme enquanto o crítico 1 persistir. A Etapa 4 e o roteiro não são atestáveis.
- **Qualidade:** alta para o contexto acadêmico. Falta fechar o importante 1 para que as evidências deixem de depender de prosa.
