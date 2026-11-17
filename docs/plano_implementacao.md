# Plano de implementação — observabilidade de crédito

**Objetivo:** entregar um pipeline financeiro reproduzível que bloqueia dados ruins, demonstra drift covariável e de conceito, registra observabilidade e consolida governança.

**Arquitetura:** aquisição UCI e contratos precedem um split exclusivo de treino, validação, referência holdout e pool de produção. Uma pipeline scikit-learn congelada alimenta cenários controlados, comparação estatística/Evidently e consolidação HTML/MLflow.

**Tecnologias:** Python 3.11, uv/uv.lock, pandas, Pandera, scikit-learn, scipy, Evidently, MLflow, PyYAML, joblib, pytest e Ruff; leitura XLS compatível com o arquivo oficial e coleta de recursos compatível com Windows.

**Especificação:** [arquitetura.md](arquitetura.md) e [enunciado preservado](enunciado.md). O retrato atual é `20261116T220412_87839641f75d`, produzido a partir da revisão `11dd2b8` com `git_dirty=false`, 38,67498 s, 22 eventos e oito alertas; pai MLflow `b987bfd1e9a848179a2bdeec3eb526fc`. As 31 fontes mantêm SHA agregado `312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73`. Os registros de verificação identificam os comandos executados e sua correspondência com as fontes.

## Restrições globais

- Dataset público financeiro binário com pelo menos 5.000 registros; usar UCI Default of Credit Card Clients, 30.000.
- Split estratificado e exclusivo por ID: treino 50%, validação 15%, referência 15%, pool de produção 20%; seed 42.
- Pandera antes do treino e da inferência; nenhum reparo silencioso de um lote inválido.
- Parâmetros em `params.yaml`, ambiente separado de parâmetros; dependências próprias congeladas em `uv.lock`.
- Não ajustar modelo em referência ou produção; limiar predefinido em 0,30; não usar alvo na seleção covariável.
- Cenários de 2.500 registros, IDs únicos por lote, mudanças sintéticas declaradas e rótulos indisponíveis tratados explicitamente.
- Entrega local sem credenciais obrigatórias; dados completos, stores, caches e segredos fora do Git.
- Histórico semântico por componente, com evidências vinculadas às fontes.

## Pontos de revisão

1. XLS com cabeçalho errado, código categórico não descrito ou saldo negativo legítimo: interpretar sem corromper e falhar antes do modelo se o contrato não for satisfeito.
2. IDs duplicados, atributos proibidos e ajuste fora do treino: bloquear vazamento e demonstrar exclusão de partições.
3. Lote vazio, sem alvo ou com uma classe: produzir status e cobertura explícitos, sem métricas fabricadas.
4. Distribuição constante, bins repetidos e categoria ausente: estatísticas finitas e comparáveis com bordas fixas.
5. Falha de tracking ou relatório incompleto: persistir erro e não declarar execução rastreada/concluída.

## Arquivos e interfaces compartilhadas

```text
params.yaml                         parâmetros e limiares
pyproject.toml / uv.lock             pacote, dependências e comandos de qualidade
src/credito_monitorado/
  config.py                         leitura e validação da configuração
  data.py                           aquisição, normalização, split e manifestos
  contracts.py                      contratos e erro de bloqueio
  model.py                          pipeline, limiar e predições
  drift.py                          cenários e estatística explícita
  monitoring.py                     adapter Evidently e avaliação supervisionada
  telemetry.py                      logs estruturados, alertas e recursos
  tracking.py                       runs e artefatos MLflow
  fairness.py                       auditoria agregada de sexo/faixa etária
  reporting.py                      HTML agregado e índice dos artefatos
  pipeline.py                       orquestração e estados de execução
  cli.py                            interface de linha de comando
tests/                              testes de contratos, leakage, estatística e integração
docs/                               arquitetura, plano, cards, causalidade e auditoria
artifacts/<execution_id>/            evidências geradas (fora do Git por padrão)
.github/workflows/ci.yml             lint, testes e smoke reproduzível
```

As interfaces abaixo são contratos de integração; classes de resultado devem ter campos serializáveis e documentação. Se um nome mudar, atualizar consumidores e este plano no mesmo bloco.

| Módulo | Interface acordada | Resultado |
|---|---|---|
| `config.py` | `load_config(path: Path) -> dict` | Configuração validada, seed e limiares |
| `data.py` | `acquire_dataset(cache_dir: Path) -> Path` | Arquivo oficial local com manifesto/hash |
| `data.py` | `load_dataset(path: Path, min_rows: int = 5000) -> pd.DataFrame` | Colunas normalizadas, integridade XLS verificada e mínimo consumido |
| `data.py` | `split_dataset(df: pd.DataFrame, seed: int = 42) -> dict[str, pd.DataFrame]` | `train`, `validation`, `reference`, `production_pool` |
| `contracts.py` | `validate_batch(df: pd.DataFrame, require_target: bool = True) -> pd.DataFrame` | Mesmo lote validado ou `DataContractError` |
| `model.py` | `train_baseline(train: pd.DataFrame, validation: pd.DataFrame, config: dict) -> TrainingResult` | `pipeline`, `threshold`, `metrics` |
| `model.py` | `predict(pipeline, df: pd.DataFrame, threshold: float) -> pd.DataFrame` | `record_id`, `probability`, `prediction` |
| `drift.py` | `build_scenarios(production_pool: pd.DataFrame, reference: pd.DataFrame, config: dict) -> dict[str, pd.DataFrame]` | `control`, `covariate`, `concept`, `combined` |
| `drift.py` | `compute_drift(reference: pd.DataFrame, current: pd.DataFrame, config: dict) -> dict` | Método/score/limiar/decisão por atributo e resumo |
| `monitoring.py` | `evaluate_scenario(reference, current, model, threshold, output_dir: Path, config: dict) -> dict` | Métricas, relatório Evidently e status de rótulos |
| `monitoring.py` | `compare_concept(control, concept, control_probabilities, concept_probabilities, config: dict) -> dict` | Invariantes e bootstrap pareado, também para combinado/covariável |
| `telemetry.py` | `Telemetry(output_dir: Path)`; `stage(...)`; `alert(...)`; `check_health(...)` | Eventos seguros, recursos e alertas persistidos |
| `fairness.py` | `audit_groups(df, probabilities, threshold: float, min_group_size: int = 30) -> dict` | Taxas/gaps descritivos, grupos pequenos suprimidos |
| `tracking.py` | `track_execution(summary: dict, artifacts_dir: Path, tracking_uri: str) -> str` | `run_id` MLflow ou erro explícito |
| `tracking.py` | `finalize_tracking(summary: dict, artifacts_dir: Path, tracking_uri: str) -> None` | Métricas e artefatos finais sincronizados |
| `tracking.py` | `sync_tracking_artifacts(summary: dict, artifacts_dir: Path, tracking_uri: str) -> None` | Árvore do relatório consolidado e cenários anexada ao run pai |
| `reporting.py` | `render_summary(summary: dict, output_dir: Path) -> Path` | HTML local com links relativos |
| `pipeline.py` | `run_pipeline(config_path: Path, output_dir: Path, data_dir: Path = Path("data/raw"), tracking_uri: str \| None = None) -> dict` | Resumo completo; falhas inesperadas relançadas e CLI com código não zero |

`record_id`, `sex`, `education`, `marriage` e `target` são excluídos das features de inferência. Eventos JSONL incluem `execution_id`, estágio, estado, duração, volume e recursos; resumos hierárquicos acrescentam cenário, hashes e métricas. Alertas incluem `code`, `severity`, `observed`, `threshold`, `message` e `recommended_action`, sem dados individuais. O HTML próprio e o MLflow consomem os mesmos resumos; o Evidently complementar conserva seus testes brutos, cuja diferença para a política BH/efeito é declarada. O bundle persistido contém `pipeline`, `threshold` e `features`; `predict` recebe pipeline/limiar extraídos dele.

## Bloco 1 — dados, contratos e modelo

**Arquivos:** `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`, `params.yaml`, `config.py`, `data.py`, `contracts.py`, `model.py`; testes `tests/test_data_model.py` e `tests/test_contracts.py`.

**Consome:** URL/licença e schema da arquitetura. **Produz:** partições normalizadas, modelo congelado e interfaces da tabela acima.

- [x] Configurar ambiente Python 3.11 com uv, dependências compatíveis, pacote src e seed; verificar lock, importações e leitura XLS no fluxo real.
- [x] Escrever testes de normalização/cache e integridade: cache íntegro evita rede e hash divergente falha antes da leitura. A integração real valida o XLS oficial, com 30.000 IDs observados no manifesto.
- [x] Implementar aquisição e manifesto sem registrar linhas individuais; atribuir a UCI/CC BY 4.0 no dicionário e README.
- [x] Escrever testes de contrato: lote válido passa; nulo, infinito, idade 18, ID duplicado, limite zero e alvo fora de {0,1} falham; saldo de fatura negativo passa; estados de atraso são inteiros -2 a 8. Na inferência alvo/demográficos excluídos são opcionais, validados quando presentes.
- [x] Implementar contrato Pandera com rejeição integral e erro sanitizado sem contexto contendo valores; preservar regras de códigos observados e não converter falhas em remoção de linhas.
- [x] Testar proporções, exclusão mútua, cobertura, seed e classes; conferir na execução real as contagens 15.000/4.500/4.500/6.000, soma 30.000.
- [x] Implementar split, manifestos e hashes. Conferir ajuste somente em treino por inspeção e testar exclusão de campos proibidos nas probabilidades.
- [x] Implementar `HistGradientBoostingClassifier` com seleção de atributos persistida, `max_iter=150`, `learning_rate=0.08`, `max_leaf_nodes=15`, comparação Dummy e limiar fixo 0,30. Guardar lista/ordem de atributos, seed e versões.
- [x] Cobrir `tests/test_data_model.py` e `tests/test_contracts.py` pela suíte global; executar treino real, superar AUROC 0,65/Dummy e comparar predições antes/depois de carregar o bundle confiável.
- [x] Registrar evidências de dados/modelo na execução final e no snapshot agregado.
- [x] Versionar os módulos de aquisição, contratos e treinamento: `734d66e`.

**Aceite independente:** dataset obtido com proveniência, pelo menos três falhas rígidas bloqueadas, partições exclusivas e modelo reproduzível treinado sem vazamento.

## Bloco 2 — cenários e detecção de drift

**Arquivos:** `drift.py`, `monitoring.py`, parâmetros de simulação/detecção; testes `tests/test_drift.py` e `tests/test_monitoring.py`.

**Consome:** partições/modelo do bloco 1. **Produz:** quatro lotes, resultados estatísticos normalizados e relatórios Evidently.

- [x] Testar IDs únicos, pertencimento ao pool, preservação dos rótulos originais e seleção independente de y; conferir lotes de 2.500 na execução UCI e cadeia em três seeds sintéticas.
- [x] Implementar pesos fixos: 3 para `limit_bal <= mediana_reference`, multiplicado por 4 para `pay_0 >= 1`, com seeds explícitas por cenário.
- [x] Testar invariância de atributos/IDs/ordem e restrição das inversões a `pay_0 <= 0`; implementar p=0,8 e intervenção consistente por ID/seed no conceito/combinado; conferir probabilidades idênticas nos pares.
- [x] Implementar manifesto de seleção e alterações sintéticas; identificar sobreposição entre cenários contrafactuais e limitar alegações de causalidade.
- [x] Testar distribuições iguais, deslocamento forte, PSI finito com categoria ausente/referência constante e correção BH conhecida; conferir bins fixos e exclusão de IDs/alvo da família estatística.
- [x] Implementar KS com p ajustado BH a 5% e D >= 0,10, PSI >= 0,20 com epsilon 1e-6, bins contínuos por referência e bootstrap pareado de Brier com 500 reamostragens; exigir pelo menos 200 linhas para comparação. Usar `brier_increase_threshold=0.05` para conceito e reportar queda complementar de AUROC com `auc_drop_threshold=0.05`.
- [x] Implementar adapter Evidently na versão do lock: colunas tipadas, IDs/metadados fora das features, métodos/limiares explícitos e HTML/JSON reais exportados; banner diferencia a política primária dos testes brutos.
- [x] Implementar ausência de alvo e classe única: status `pending_labels` ou métrica indefinida com motivo, sem tratar ausência como estabilidade de conceito.
- [x] Cobrir `tests/test_drift.py` e `tests/test_monitoring.py` pela suíte global; conferir drift nas duas variáveis e delta Brier/IC nos pares conceito/controle e combinado/covariável reais.
- [x] Inspecionar automaticamente HTML/JSON, conteúdo, links, scores, cobertura e limites; registrar achados e correções na auditoria.
- [ ] Inspeção visual manual dos HTMLs: não realizada; conteúdo, links e integridade têm verificação automatizada.
- [x] Criar commit semântico de drift: `2b8c3bc`.

**Aceite independente:** drift covariável material em duas variáveis e conceito isolado com X invariável, ambos demonstrados por evidência estatística e HTML. Não usar um rótulo de cenário como resultado do detector.

## Bloco 3 — observabilidade, integração e execução

**Arquivos:** `telemetry.py`, `tracking.py`, `fairness.py`, `reporting.py`, `pipeline.py`, `cli.py`, script/configuração de execução, testes `tests/test_telemetry.py`, `tests/test_fairness.py`, `tests/test_pipeline.py` e workflow CI.

**Consome:** lotes/resultados/relatórios dos blocos anteriores. **Produz:** execução integrada, logs/alertas, MLflow e HTML consolidado.

- [x] Escrever teste de orquestração: validação antecede treino/inferência; lote inválido não chama modelo; falha inesperada interrompe dependentes; bloqueio esperado da demonstração tem resultado separado.
- [x] Implementar execução por `uv run python -m credito_monitorado.cli run --config params.yaml --output artifacts`, com diretório único por execução e manifesto inicial/final. Não sobrescrever evidência anterior silenciosamente.
- [x] Emitir logs JSONL e alertas JSON pelos schemas compartilhados; medir status, duração, volumes, cobertura, RSS e disco com funcionamento no Windows.
- [x] Registrar execução/cenários no MLflow SQLite local e anexar configuração, métricas, manifestos e relatórios. Testar escrita/leitura real, encerramento de runs e erro de tracking explícito.
- [x] Gerar HTML consolidado local, links relativos válidos, resumo de saúde e todos os cenários. Exibir estados insuficientes/indefinidos como pendentes.
- [x] Cobrir telemetria, equidade e integração pela suíte de testes; conferir SQLite pai/filhos, artefatos baixados, links e métricas por consultas automatizadas.
- [x] Configurar CI para `uv sync --frozen`, Ruff e pytest sem credenciais; executar a integração local separadamente, com skip explícito em cache ausente. O estado de cada execução de CI está disponível no GitHub Actions.
- [x] Executar Ruff/formatação/pytest e registrar resultados reais: 150 testes passaram; conferir sete logs literais, JUnit, artefatos e hashes da execução UCI final.
- [x] Criar commit semântico de observabilidade: `5152b36`.

**Aceite independente:** uma execução permite rastrear do contrato ao alerta, com visualização de sucesso/falha/recursos e evidência MLflow recuperável. Não basta instalar a biblioteca ou produzir um HTML vazio.

## Bloco 4 — documentação, governança e auditoria

**Arquivos:** `README.md`, `docs/dicionario_dados.md`, `docs/model_card.md`, `docs/causalidade.md`, `docs/matriz_rastreabilidade.md` e relatório de auditoria/revisão.

**Consome:** somente resultados efetivamente executados e manifestos finais. **Produz:** instruções reproduzíveis, governança consolidada, apresentação em vídeo e histórico de correções.

- [x] Consolidar no README propósito, setup uv, reprodução, comandos de verificação e interpretação dos alertas; publicar indicadores e identificadores da execução, configuração, dados e modelo.
- [x] Escrever cards: nomes/unidades/códigos, Taiwan/2005, limite de crédito diferente de renda, licença/atribuição, exclusão de atributos, vieses, ausência de validação para concessão real e limitações de generalização.
- [x] Resumir governança no README e detalhá-la em `docs/governanca.md`: finalidade, minimização, responsáveis, base legal contextualizada, direitos, retenção, acesso, incidentes e equidade.
- [x] Documentar causalidade: seleção covariável dependente somente de X, contrafactual de rótulos, invariantes, métricas observadas, hipóteses alternativas reais e plano de investigação; declarar ausência de inferência causal macroeconômica.
- [x] Publicar o [vídeo STAR](https://youtu.be/0NyRf1oxfeI), com situação, tarefa, ação, resultados e governança, em até cinco minutos.
- [x] Preencher matriz R01–R10 com artefatos/verificações/resultados; relacionar o vídeo e os artefatos de demonstração ao critério de apresentação.
- [x] Registrar revisões técnicas com identificação dos arquivos, achados e tratamento, usando apenas código e evidências agregadas.
- [x] Tratar os achados A01–A05 com evidências de código, testes e execução.
- [x] Fechar URI ambígua por omissão integral de metadados remotos e validar o helper de integridade por bytes, configuração, ID e manifesto; conferir regressões/evidências da versão final.
- [x] Isolar os três casos negativos de ID, estado e escape de diretório, com resultados identificados no JUnit.
- [x] Validar UTF-8, integridade, links relativos e correspondência entre documentação e implementação.

**Aceite independente:** um avaliador consegue reproduzir a demonstração e associar cada requisito ao artefato correto; o README contém governança e referencia o vídeo publicado.

## Portas de aceite

| Porta | Condições para avançar |
|---|---|
| Dados/modelo | Proveniência, contrato, split exclusivo, fit só em treino e métrica mínima comprovados |
| Estatística | Dois atributos com drift, invariância X no conceito e degradação pareada comprovadas |
| Operação | Logs/alertas/recursos/HTML/MLflow realmente gerados e recuperáveis |
| Entrega | README e matriz consistentes, revisão adversarial tratada, verificações executadas e vídeo da demonstração publicado |

As portas de aceite são verificadas pelos resultados e artefatos identificados em [resultados](resultados.md) e na [matriz de rastreabilidade](matriz_rastreabilidade.md).
