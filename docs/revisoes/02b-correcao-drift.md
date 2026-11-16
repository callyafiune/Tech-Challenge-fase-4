# Revisão adversarial — 02b-correcao-drift

Modelo solicitado: `fable`. Modelo retornado: `claude-fable-5-2`.

# Revisão adversarial: drift, monitoramento, contrato, testes e causalidade

Revisão por leitura estática: nada foi executado e o pacote não traz logs nem artefatos. Nenhum resultado (testes passando, HTML gerado, drift detectado no UCI) está comprovado.

## Críticos

Nenhum defeito crítico demonstrável por leitura. Não encontrei crash, erro numérico nem vazamento treino/teste comprovado nos três módulos; BH, PSI, a seleção só por X e a inversão por hash estão corretos.

## Importantes

1. **Não há decisão de degradação para lote real** (`monitoring.compare_concept`, `evaluate_scenario`).
   - Problema: com X e predições idênticos, a diferença pareada só é não nula nas linhas invertidas pelo simulador, onde vale `(1−2y)(1−2p)`. O teste mede a qualidade do modelo nos rótulos originais vezes a fração invertida, não uma capacidade de detecção.
   - Problema: `performance` e `reference_performance` são apenas descritivos, `auc_drop_threshold` não entra em nenhuma regra e `concept_status` nunca sai de `requires_pair` neste pacote.
   - Impacto: um lote rotulado sem contrafactual não recebe nenhum veredito de degradação.
   - Correção: criar regra não pareada (ΔBrier/ΔAUC contra a referência, com IC bootstrap) e renomear a flag para `intervention_confirmed`.

2. **Evidência de execução ausente.**
   - `docs/causalidade.md` remete a `resultados.md`, que não aparece no estado do git informado (pode ser gerado e ignorado; não é verificável).
   - `test_cadeia_real_uci...` dá `skip` silencioso sem o cache local, então em CI sem dados a cadeia real nunca roda.
   - `_export_evidently` só é exercitado por um teste marcado `integracao`; os demais o substituem por monkeypatch.
   - Correção: versionar o resultado agregado e fazer o CI falhar, ou reportar, quando esses testes não rodarem.

3. **Metadados da simulação ainda dependem de `DataFrame.attrs` e não têm teste** (`evaluate_scenario`).
   - Problema: se `attrs` se perder (parquet, CSV, concat), um lote com rótulos invertidos é gravado como `available_labels` e `simulation: {}`.
   - Problema: nenhum teste passa uma saída de `build_scenarios` por `evaluate_scenario` nem verifica `simulation` ou `labels_status` no JSON.
   - Correção: passar os metadados como argumento explícito e testar o cenário `concept` de ponta a ponta.

4. **Aviso no HTML do Evidently é frágil** (`_export_evidently`).
   - Problema: a regex insere o aviso na primeira ocorrência de `<body` no arquivo inteiro. Se o JS embutido no HTML contiver essa string antes do corpo real (risco não confirmado), o aviso cai dentro do script. O teste só verifica que o texto existe, não onde está.
   - Problema: se a inserção falhar, o HTML sem aviso permanece em disco.
   - Problema: no controle, com 14 contínuas e p bruto, a chance de ao menos um falso positivo no Evidently chega a cerca de 51% sob independência. Não há teste de concordância com `monitoring.json`.
   - Correção: gravar em arquivo temporário, validar a posição do aviso, remover o arquivo em caso de falha e testar a concordância nos quatro cenários.

5. **A mensagem da exceção ainda se propaga** (`evaluate_scenario`).
   - Problema: o JSON guarda só `error_type`, mas o `raise` reenvia a mensagem original. O próprio teste confirma isso com `match=segredo`.
   - Impacto: a garantia de privacidade depende de `cli.py` e `telemetry.py`, que estão fora do pacote.
   - Correção: relançar um erro sanitizado com `from None`, ou provar a sanitização na borda.

6. **Guarda de separação é parcial** (`_require_disjoint_ids`).
   - Problema: ela cobre só referência × pool e só por `record_id`. Treino/validação × pool não é verificado em nenhum ponto do pacote, nem no teste real.
   - Impacto: a afirmação "não usada no treino" do documento não tem prova aqui.
   - Correção: verificar a disjunção de todas as partições em `split_dataset` e testá-la.

## Menores

- **Limiar oculto:** `brier_increase_threshold` e `psi_epsilon` não aparecem na configuração de teste, que diz espelhar a demonstração. Se também faltarem em `params.yaml`, a decisão usa valores padrão do código.
- **BH pouco efetivo:** com n=2.500, todo D ≥ 0,10 tem p ≈ 0, então a decisão é só o limiar de efeito, sem IC para D. A família BH não cobre os quatro cenários.
- **PSI contínuo:** se 90% ou mais da referência estiver no valor mínimo, sobra um único intervalo útil e deslocamentos para cima ficam invisíveis. Isso afeta `psi_drift` do score.
- **Amostragem:** `build_scenarios` depende da ordem das linhas do pool. Ordenar por `record_id` antes de sortear resolve.
- **Contrato:**
  - a docstring de `validate_batch` promete validar tipos, mas não há dtype imposto (`record_id` float passa);
  - `REQUIRED_COLUMNS` não é usado;
  - exceções do Pandera fora das quatro capturadas escapam com contexto.
- **Fixtures:**
  - `referencia_independente()` é o próprio pool com IDs deslocados, não uma amostra independente;
  - `from test_drift import` depende do modo de importação do pytest.
- **Caminhos sem teste:**
  - porta de efeito (p significativo com D < 0,10);
  - `insufficient_sample` e `single_class`;
  - rótulos parciais;
  - taxa de inversão próxima de 0,8;
  - falha de `_write_aggregate`;
  - decisão `drift` do score;
  - conteúdo numérico de `evidently.json`.
- **Pendências anteriores:**
  - `compare_concept` exige `low > 0`, não `low >= limiar`;
  - `selection_weights` é ignorado em favor de `weights`;
  - `monitoring.json` não tem versão do modelo, hash dos dados nem timestamp.
- **Features:** `age` é feature enquanto os demais demográficos foram excluídos. A justificativa deveria estar no model card, que está fora do pacote.

## Situação dos itens da revisão 02

| Item | Situação pelo código atual |
|---|---|
| 1 Conceito circular | Aberto; apenas documentado como verificação de sanidade |
| 2 HTML contraditório | Parcial: aviso inserido, sem teste de concordância |
| 3 Cadeia simulação→detecção | Resolvido no sintético (3 sementes); o real depende do cache |
| 4 Sobreposição de IDs | Resolvido para referência × pool |
| 5 Drift de score e taxa | Resolvido (`_prediction_monitoring`) |
| 6 Metadados no JSON | Parcial: gravados, mas vindos de `attrs` e sem teste |
| 7 JSON primário atômico | Resolvido e testado |
| 8 Calibração e poder | Aberto; declarado como limitação |
| 9 KS em nominais | Não se aplica: `FEATURES` exclui os demográficos |
| 10 Dimensão temporal | Aberto; o documento assume que não há coortes |

## Não verificável neste pacote

- **Arquivos ausentes:** `model.py`, `data.py`, `pipeline.py`, `cli.py`, `params.yaml`, `pyproject.toml`, o CI e o enunciado.
- **Consequências:** não posso confirmar:
  - quem chama `compare_concept`;
  - se `predict` aplica o contrato;
  - o tamanho do pool, do qual depende o cenário covariável atingir PSI ≥ 0,20 em `pay_0`;
  - o pin da API 0.7 do Evidently;
  - se o HTML embute dados por registro.
- **Aderência:** os requisitos foram avaliados só indiretamente, pelas citações da revisão anterior.

## Veredito

- **Conformidade:** parcial e não comprovada. A detecção de drift em X e no score está plausivelmente atendida no código, mas a degradação supervisionada só existe para a intervenção simulada (item 1), a passagem do tempo não é simulada e não há prova de execução (item 2).
- **Qualidade:** boa, com ressalvas. A estatística central, a gravação atômica e o contrato sem vazamento de valores estão corretos pela leitura. Os itens 1 a 4 devem ser corrigidos antes da entrega.
