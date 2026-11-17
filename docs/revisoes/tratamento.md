# Revisões técnicas e tratamento dos achados

Os pareceres são publicados em edição técnica, com achados e conclusões referentes às versões identificadas nos metadados. São leituras estáticas, complementares à execução de testes e à conferência dos artefatos. A implementação atual é comprovada pelos registros de verificação e pelos resultados publicados.

| Área | Tratamento implementado | Evidência |
|---|---|---|
| Dados e contratos | Integridade do cache, domínios explícitos, bloqueio do lote e erros sem valores individuais. | `contracts.py`, testes e campo `contracts` do resumo. |
| Isolamento | IDs exclusivos entre partições; ajuste apenas no treino; ID, alvo, sexo, escolaridade e estado civil fora dos preditores. | `data.py`, `model.py` e testes de separação. |
| Estatística | KS com BH e tamanho de efeito; PSI nas discretas; política primária separada dos testes brutos do Evidently. | [Resultados](../resultados.md) e [causalidade](../causalidade.md). |
| Conceito simulado | Comparação pareada com entradas e probabilidades invariáveis; bootstrap do aumento de Brier. | Cenários controle/conceito e covariável/combinado. |
| Privacidade | Omissão integral de destinos remotos e sanitização dos erros persistidos. | `_safe_tracking_uri`, regressões de URI e [governança](../governanca.md). |
| Observabilidade | Métricas finais coerentes entre resumo e MLflow; relatórios espelhados na árvore do run pai. | [Metadados MLflow](../evidencias_mlflow.json) e testes SQLite/download. |
| Estados indefinidos | Amostra insuficiente e rótulos ausentes permanecem explícitos no JSON e no HTML. | `monitoring.py`, `reporting.py` e testes de borda. |
| Equidade | Supressão por tamanho, supressão complementar e denominadores mínimos por métrica. | `fairness.py` e auditoria agregada no painel. |
| Integridade | Verificação de ID, estado, configuração, inventário e hashes; fixtures negativas isoladas. | `scripts/verificar_entrega.py`, JUnit e [registro](../verificacao.json). |
| Docker | Imagem de execução, usuário sem privilégios, volumes, rede bloqueada e coleta sequencial de evidências. | [Tratamento Docker](08-docker-tratamento.md) e [verificação](../verificacao_docker.json). |

## Rastreabilidade dos achados de integração

| Achado do parecer 03b | Estado e evidência atual |
|---|---|
| Histórico das fontes e registro de execução | O manifesto identifica a revisão `11dd2b8` e 31 hashes de fontes/configuração. A [captura da CLI](../execucao_cli.json) registra o processo e sua saída; o [índice de verificação](../verificacao.json) reúne logs e JUnit. |
| Menor 1 — contador da demonstração de contrato | O bloqueio vem do contrato antes da inferência. O contador da demonstração expressa a garantia do fluxo; não representa instrumentação remota de chamadas ao modelo. |
| Menor 2 — seleção de `failed_stage` | O handler filtra eventos com `expected_failure`; o teste de falha após bloqueio esperado verifica o diagnóstico `pipeline`. |
| Menor 3 — URI e caminhos locais | Destinos remotos são omitidos integralmente. Caminhos locais podem aparecer nas evidências; essa exposição de metadados está descrita na governança. |
| Menor 4 — falha após criação do run | O handler tenta marcar o run como `FAILED`. A cobertura não comprova todos os pontos de interrupção; parada forçada pode deixar registros incompletos. |
| Menor 5 — HTML nos runs filhos | Os filhos contêm estatísticas e referência ao pai; os HTMLs e seus arquivos relativos são sincronizados na árvore do pai. |
| Menor 6 — saúde das últimas etapas | Finalização e sincronização têm duração registrada; a avaliação de alertas ocorre antes de sua conclusão. A cobertura de alertas dessas etapas finais é limitada. |
| Menor 7 — processo da CLI | O verificador Docker executa a CLI com saídas zero nos cenários válidos e saída 1 com cache vazio e rede bloqueada. |
| `label_names` | `original_labels` é apresentado como `observados` no relatório. |
| `counterfactual` no controle | O metadado também marca a amostra de controle simulada; a condição dos rótulos é descrita por `labels_status`. O controle conserva os rótulos originais. |
| PSI e banner do Evidently | O PSI primário de `pay_0` é 0,205308, e o bruto do Evidently é 0,202018. O banner identifica políticas diferentes; a margem e a ausência de IC do PSI estão em [resultados](../resultados.md). |

## Pareceres de referência

- Arquitetura: [00](00-arquitetura.md).
- Dados e modelo: [01](01-dados-modelo.md), [01b](01b-correcao-dados.md).
- Drift: [02](02-drift-estatistica.md), [02b](02b-correcao-drift.md).
- Observabilidade e integridade: [03](03-observabilidade.md), [03b](03b-integracao-corrigida.md), [03c](03c-metadados-finais.md), [03d](03d-integridade-fechamento.md), [03e](03e-cobertura-isolada.md).
- Documentação e governança: [04](04-documentacao-governanca.md), [04b](04b-documentacao-corrigida.md).
- Docker: [08](08-docker.md), [08b](08b-docker-fechamento.md), [08c](08c-docker-evidencias.md).

## Limites de interpretação

As conclusões de cada parecer dependem dos arquivos analisados naquela versão. A ausência de um arquivo em um pacote de revisão não demonstra sua ausência no repositório completo. O estado atual dos achados é apresentado na tabela acima e na [auditoria técnica](../auditoria_final.md).

O modelo mantém limitações de generalização, calibração operacional e equidade. A simulação severa verifica a cadeia de detecção, sem estimar sensibilidade para mudanças pequenas ou causas macroeconômicas. A supressão aplicada à auditoria por grupos não torna automaticamente anônimos todos os histogramas do Evidently.

Os HTMLs têm verificações automatizadas de conteúdo, links e integridade. Os logs e o JUnit comprovam execução; os pareceres não constituem inspeção visual manual ou certificação de produção.
