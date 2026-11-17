# Revisão adversarial — 02-drift-estatistica

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão adversarial: `drift.py`, `monitoring.py`, testes e `params.yaml`

Revisão por leitura estática: nada foi executado e o pacote não traz logs nem artefatos, então nenhum resultado (testes passando, HTML gerado, drift apontado) está comprovado.

## Críticos

Nenhum defeito crítico demonstrável por leitura: não encontrei crash, erro numérico nem vazamento comprovado nos dois módulos.

## Importantes

1. **Detecção de concept drift circular** (`monitoring.compare_concept`, `evaluate_scenario`).
   - Problema: o teste exige X e predições idênticos, então só mede os rótulos que o próprio simulador inverteu. `evaluate_scenario` devolve sempre `requires_pair`.
   - Impacto: não existe detector para lote real, sem contrafactual.
   - Correção: adicionar um detector não pareado (queda de Brier/AUC contra referência holdout com IC, de preferência reponderada por importância) e renomear a flag para algo como `intervention_confirmed`.

2. **HTML do Evidently pode contradizer a decisão do projeto** (`_export_evidently`).
   - Problema: o Evidently usa KS com p bruto, sem BH nem efeito mínimo, e regra agregada própria.
   - Impacto: no controle, com cerca de 17 contínuas, a chance de ao menos um falso positivo é da ordem de 1−0,95¹⁷ ≈ 58%. No cenário covariável, a lista de variáveis do HTML tende a divergir de `monitoring.json`. O HTML é o entregável da Etapa 2 e o aviso `differences` não aparece nele.
   - Correção: gerar um painel próprio com a decisão primária ao lado e testar a concordância nos quatro cenários.

3. **Cadeia simulação→detecção sem teste** (`tests/test_drift.py`).
   - Problema: nenhum teste passa a saída de `build_scenarios` por `compute_drift`. O teste de drift usa `assign(limit_bal=1500000, pay_0=8)` e o controle é uma cópia idêntica (D=0).
   - Impacto: não há prova de que os pesos 3.0/4.0 acionam `limit_bal` e `pay_0` (requisito de duas ou mais variáveis), nem de que o controle reamostrado fica estável.
   - Correção: testar `covariate` (as duas variáveis em `drifted_features`) e `control` (sem drift) em várias sementes.

4. **Separação referência/produção não imposta** (`build_scenarios`, `evaluate_scenario`).
   - Problema: sobreposição de `record_id` é aceita. O próprio teste passa `pool.iloc[:200]` como referência.
   - Impacto: se a referência for o treino (não verificável), `reference_performance` e o `ClassificationPreset` comparam métrica in-sample com out-of-sample, e a "degradação" aparece até no controle.
   - Correção: guarda de interseção vazia e métricas de referência em holdout.

5. **Sem drift de predição nem de prevalência** (`compute_drift`).
   - Problema: só X é monitorado.
   - Impacto: com rótulos pendentes, o modelo fica sem nenhum sinal de saúde (Etapa 3).
   - Correção: KS/PSI do score e taxa de positivos no limiar.

6. **Metadados da simulação só em `DataFrame.attrs`** (`build_scenarios` → `evaluate_scenario`).
   - Problema: sementes, `flipped_rows` e `eligible_rows` não vão para `monitoring.json`. `attrs` se perde em CSV, concat ou validação.
   - Impacto: um lote com rótulos invertidos passa a ser reportado como `available_labels`.
   - Correção: retornar os metadados explicitamente e gravá-los no JSON.

7. **Falha do relatório complementar derruba o primário** (`evaluate_scenario`).
   - Problema: `monitoring.json` só é escrito depois do Evidently, e `allow_nan=False` pode falhar com o HTML já gravado.
   - Impacto: perda da decisão primária ou artefatos parciais.
   - Correção: gravar o JSON primeiro, de forma atômica, e registrar o status do Evidently.

8. **Sem calibração estatística** (`build_scenarios`, `params.yaml`).
   - Problema: há uma única semente e lote, e a inversão de 0.8 é extrema. Pelas taxas conhecidas do UCI, P(Y=1 | pay_0≤0) vai de cerca de 14% para cerca de 72% (estimativa, não executada).
   - Impacto: a detecção é trivial e não há evidência de taxa de falso positivo nem de poder para os limiares 0.10/0.20/0.05.
   - Correção: rodar várias sementes e uma curva de sensibilidade (flip de 5% a 80%).

9. **KS em variáveis nominais** (`compute_drift`; condicional a `FEATURES`, que não está no pacote).
   - Problema: se `sex`, `education` e `marriage` forem features, entram como contínuas, pois só `PAY_COLUMNS` é categórica.
   - Impacto: KS sobre códigos sem ordem é inválido e contamina a família BH.
   - Correção: tratá-las com PSI ou qui-quadrado.

10. **Sem dimensão temporal** (`build_scenarios`).
    - Problema: são quatro lotes estáticos.
    - Impacto: o enunciado pede "passagem do tempo" e degradação "ao longo do tempo".
    - Correção: gerar uma sequência de janelas com intensidade crescente.

## Menores

- **Parâmetro morto:** `auc_drop_threshold` é reportado, mas não entra em nenhuma decisão.
- **Rótulos parciais:** `_performance` fixa `label_coverage=1.0`, e um lote parcialmente rotulado perde toda a métrica.
- **Teste de integração fraco:** o nome promete "json com números recuperáveis", mas `evidently.json` nunca é aberto. `limit_bal` em `linspace` deixa referência e atual disjuntos (D=1) sem asserção. O marcador `integracao` pode ser desselecionado.
- **Caminhos sem teste:**
  - porta de efeito (p significativo com D<0.10);
  - `insufficient_sample` e `single_class`;
  - erros de `build_scenarios`;
  - taxa de inversão próxima de 0.8;
  - PSI contínuo com empates;
  - igualdade exata de `drifted_features`.
- **Fixtures frágeis:** `from test_drift import` depende do modo de importação do pytest, e `criar_base` exige múltiplo de 5.
- **Regra de decisão:** `compare_concept` exige `low > 0`, não `low >= limiar`.
- **PSI:** é sensível a `epsilon` em células vazias e não tem incerteza amostral.
- **Multiplicidade:** BH não cobre os quatro cenários nem janelas repetidas.
- **Código:**
  - `selection_weights` é ignorado em favor de `weights`;
  - os pesos não passam por `float()`;
  - as predições da referência são recalculadas a cada cenário;
  - o esquema do resultado varia conforme o `status`.
- **Rastreabilidade:** `monitoring.json` não tem timestamp, versão do modelo nem hash de dados, e `params.yaml` não tem checksum do dataset.

## Não verificável neste pacote

- **Arquivos ausentes:** `contracts.py`, `model.py`, scripts, README/LGPD, MLflow, `pyproject.toml` e `uv.lock`.
- **Consequência:** não posso julgar Etapa 1, Etapa 3, governança, o pin da API 0.7 do Evidently nem a alegação "o predictor aplica o contrato".
- **Fora do pacote:** o snapshot do git mostra tudo não rastreado e um único commit, o que hoje não atende ao requisito de histórico semântico.

## Veredito

- **Conformidade:** parcial e não comprovada. A Etapa 2 está plausivelmente atendida no código, mas sem evidência de execução e com risco de o HTML contradizer a decisão (item 2). As demais etapas não são avaliáveis aqui.
- **Qualidade:** boa, com ressalvas. BH, PSI com bordas fixadas pela referência, seleção apenas por X, inversão estável por hash e saídas agregadas sem `record_id` estão corretos pela leitura. Os itens 1 a 4 devem ser corrigidos antes da entrega.
