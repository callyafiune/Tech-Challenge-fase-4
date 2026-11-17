# Revisão adversarial — 00-arquitetura

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão adversarial: observabilidade de crédito

**Escopo real:** recebi só `docs/arquitetura.md`, `docs/plano_implementacao.md`, `params.yaml` e `pyproject.toml`. Não recebi código, testes, `uv.lock`, README, artefatos, roteiro nem o enunciado original. Não executei nada; as estimativas numéricas abaixo são cálculos analíticos meus, não medições.

## Críticos

**C1. `params.yaml` contradiz a arquitetura.**

| Tema | `params.yaml` | Arquitetura |
|---|---|---|
| Modelo | `learning_rate`, `max_leaf_nodes` (gradient boosting) | Regressão logística com padronização |
| Limiar | `threshold: 0.30` fixo, sem origem | Escolhido por F1 só na validação |
| KS | `ks_alpha: 0.05` | Benjamini-Hochberg a 1% |
| Bootstrap | `bootstrap_samples: 500` | 1.000 reamostragens |
| Conceito | `auc_drop_threshold: 0.05` | Delta de Brier ≥ 0,05 |

- **Ausentes no arquivo:** frações do split, epsilon e bins do PSI, AUROC mínimo, seeds por cenário e do bootstrap, grupo mínimo de 30, SHA-256 esperado.
- **Sem especificação:** `min_rows`, `max_stage_seconds` e `max_rss_mb` existem no arquivo, mas não na arquitetura.
- **Impacto:** o hash da configuração gravado nas evidências atestará valores que não governam o comportamento, ou o código violará a especificação.
- **Correção:** reescrever `params.yaml` a partir da arquitetura; `load_config` deve rejeitar chaves desconhecidas e ausentes; remover o limiar fixo.

**C2. O drift planejado em `pay_0` provavelmente fica abaixo ou na borda de PSI 0,20 (R05, 25%).**

- **Cálculo:** `pay_0 >= 1` é cerca de 22,7% da base. Amostrando 2.500 de 6.000 sem reposição com pesos 3×4, o grupo de peso 12 quase se esgota e a fração sobe para cerca de 40–42%.
- **Resultado estimado:** PSI entre 0,15 e 0,19 no colapso em duas categorias; o detalhamento por categoria acrescenta pouco. `limit_bal` passa com folga (D em torno de 0,20).
- **Agravante:** a mitigação "corrigir configuração com justificativa" contradiz "limiares definidos antes da avaliação" e abre espaço para ajuste depois de ver o resultado.
- **Correção:** calibrar os pesos analiticamente ou na partição de treino antes de olhar o pool (por exemplo, peso de atraso maior ou lote menor), registrar a calibração e não mexer nos limiares.

## Importantes

**I1. Duas fontes de verdade estatística (`drift.py` e adapter Evidently).**
- **Problema:** até onde sei, o KS do Evidently decide por p-valor, sem Benjamini-Hochberg nem tamanho de efeito, e o PSI dele trata zeros de outra forma. Confirmar na versão do lock.
- **Impacto:** o HTML do Evidently pode marcar drift no controle enquanto o resumo próprio diz que não, o que desmente a frase do plano sobre "evitar decisões divergentes".
- **Correção:** declarar a estatística própria como autoritativa e o Evidently como visualização; testar e documentar as discrepâncias.

**I2. Cenário de conceito extremo e critério tautológico.**
- **Problema:** inverter 80% dos rótulos em `pay_0 <= 0` (cerca de 77% do lote) altera uns 60% dos rótulos. A prevalência vai de cerca de 22% para cerca de 67% e o AUROC deve cair abaixo de 0,5.
- **Impacto:** delta de Brier ≥ 0,05 com IC > 0 passa trivialmente e não mostra sensibilidade do detector.
- **Correção:** acrescentar curva dose-resposta (probabilidades 0,05, 0,1, 0,2) e rotular o teste como verificação de sanidade.

**I3. Cenário `combined` sem critério pareado.**
- **Problema:** a regra só define `concept − control`; o par correto do combinado é `combined − covariate`. As inversões também não são consistentes por registro entre cenários que compartilham IDs.
- **Interface:** `evaluate_scenario(...)` não recebe o lote pareado, então o bootstrap pareado não tem onde ser calculado.
- **Correção:** definir o par do combinado, derivar a inversão por `hash(seed, record_id)` e incluir o lote pareado na assinatura.

**I4. Covariável sem expectativa supervisionada e controle único.**
- **Problema:** a seleção aumenta a prevalência e desloca Brier e F1 mesmo com `P(Y|X)` intacto, por um valor possivelmente próximo de 0,05. Um único sorteio de controle não calibra a taxa de falso alerta.
- **Correção:** reponderar o lote covariável pelo inverso dos pesos e mostrar que as métricas voltam ao nível do controle; repetir o controle com N seeds para obter a distribuição nula de D, PSI e Brier.

**I5. Hash esperado não está fixado em lugar nenhum.**
- **Problema:** "mudança do hash esperado exige revisão" não é verificável sem o valor em arquivo versionado. A URL aponta para um `.zip` e a arquitetura fala em XLS, sem dizer qual dos dois é hasheado.
- **Correção:** fixar o SHA-256 do zip e do XLS em `params.yaml`; exigir exatamente 30.000 linhas, não `min_rows: 5000`.

**I6. Privacidade.**
- **Falhas do Pandera:** `failure_cases` e a mensagem de `SchemaErrors` trazem valores e índices individuais. Persistir só contagens por regra e coluna.
- **Minimização:** o contrato de inferência exige `sex`, `education` e `marriage`, que o modelo não usa. Separar contrato de inferência e contrato de auditoria; `education` e `marriage` nem são auditados.
- **Idade:** `age` é preditor e também eixo de auditoria; falta justificativa de não discriminação.
- **Identificadores:** o manifesto de seleção e a saída de `predict` carregam `record_id`. Garantir que ficam fora do Git e do MLflow versionável.
- **Supressão:** grupos menores que 30 exigem supressão complementar, senão o valor sai por diferença.

**I7. Lote vazio e colunas extras (`contracts.py`).**
- **Problema:** um DataFrame vazio passa em schema Pandera por padrão. A regra "sem colunas desconhecidas" não diz o que ocorre com `target` presente quando `require_target=False`, nem com metadados de cenário.
- **Correção:** regra explícita de volume mínimo e definição do modo estrito para esses casos.

**I8. Limiar fora do artefato (`model.predict`).**
- **Problema:** `predict(pipeline, df, threshold)` recebe o limiar por fora, embora a arquitetura exija que ele viaje com o objeto persistido.
- **Correção:** prever a partir do objeto persistido, sem argumento de limiar.

**I9. Cobertura e CI.**
- **Problema:** `pytest-cov` está instalado sem meta de cobertura. O CI nunca exercita o dataset real, então "clone limpo executa verificação" (R09) só valeria para dados sintéticos. O marker `integracao` não tem política.
- **Correção:** definir `--cov-fail-under`, criar job manual com dataset em cache e hash fixado, e incluir Windows na matriz.

## Menores

- **PSI:** `epsilon=1e-6` infla o valor em categorias raras de `pay_*` (cerca de 0,005 por célula zero contra não zero). Usar suavização proporcional a n ou agrupar categorias raras.
- **Simulador e detector acoplados:** os pesos usam a mediana da `reference`, que também é a base do detector. Usar constante declarada ou mediana do treino.
- **Frase incorreta:** "os sinais deliberados não são atributos do modelo" é falsa, porque `limit_bal` e `pay_0` são atributos e são monitorados.
- **Estados:** o enum `success/blocked/failed` não cobre `pending_labels` nem falha de tracking; o código de saída nesse caso é indefinido.
- **Ordem circular:** HTML, `run_id` do MLflow e manifesto final dependem um do outro, sem ordem definida.
- **Latência:** "regressão frente a execuções comparáveis" não tem baseline; o arquivo usa teto fixo.
- **Métricas:** "AUROC > Dummy" é trivial (0,5); comparar Brier e average precision. O F1 de validação é otimista; reportar o da `reference` como estimativa limpa. A grade de limiares não está definida.
- **Hashes de tabelas:** falta serialização canônica, o que arrisca diferenças entre Windows e Linux.
- **Enunciado:** o plano cita `C:\estudos\...`, fora do repositório, então a matriz R01–R10 não é auditável e não pude conferir aderência ao enunciado.
- **Registro desta revisão:** ela cobriu só quatro arquivos; o relatório de auditoria não deve dizer que o código foi revisado.
- **LGPD:** o art. 20 não garante revisão humana (vetada em 2019); tratar como política. Falta o prazo de comunicação de incidente (art. 48 e Resolução ANPD 15/2024) e dizer que a LGPD se aplica por analogia a dados de Taiwan.
- **Nomes:** projeto `confiabilidade-credito` e pacote `credito_monitorado`.

## Veredito

- **Conformidade: não demonstrada.** O pacote é só especificação e configuração: todas as caixas do plano estão desmarcadas e o snapshot do Git mostra um único commit com tudo não rastreado. O roteiro STAR não veio no pacote e não foi avaliado.
- **Qualidade do desenho: boa**, com split exclusivo, holdout de referência, bloqueio sem reparo silencioso e limites causais explícitos.
- **Recomendação: não está pronto para execução.** Corrigir C1 e C2 antes de rodar; I1 a I5 antes de publicar qualquer resultado.
