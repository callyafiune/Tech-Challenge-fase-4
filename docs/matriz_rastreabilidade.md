# Matriz de rastreabilidade

O [enunciado](enunciado.md) é a referência de requisitos. A execução identificada em [resultados](resultados.md) é o retrato entregue; o [inventário de publicação](../reports/execucao_validada/publicacao.json) identifica cada arquivo agregado. Código, configuração e lock estão identificados por hashes no manifesto, mesmo quando a árvore Git está suja.

| Requisito | Implementação | Evidência e verificação |
|---|---|---|
| R01 — base financeira ≥ 5.000 | `data.acquire_dataset/load_dataset` | Fonte UCI real: 30.000; pins ZIP/XLS, manifesto de origem e [dicionário](dicionario_dados.md). Testes de cache e integração UCI sem rede quando há cache. |
| R02 — baseline sklearn | `model.train_baseline` | AUROC de validação 0,77357 contra Dummy 0,50; referência independente avaliada. Carregamento joblib preserva probabilidades. [Resultados](resultados.md). |
| R03 — referência/produção separadas | `data.split_dataset` e guarda da integração | 15.000/4.500/4.500/6.000, IDs disjuntos; manifestos com hashes. Testes de contagens, estratificação, seed e sobreposição. |
| R04 — contratos /25% | `contracts.validate_batch` | Pandera, controle positivo e violações isoladas de nulo, idade e duplicata; lote combinado bloqueado antes da inferência. [Resumo](../reports/execucao_validada/resumo.json), campo `contracts`; testes de regressão e erros sanitizados. |
| R05 — drift /25% | `drift.build_scenarios/compute_drift`, `monitoring.evaluate_scenario` | Política primária aponta `limit_bal` e `pay_0`; Evidently bruto aponta 15 colunas, incluindo ambas. [Evidently covariável](../reports/execucao_validada/covariate/evidently.html), scores no [JSON primário](../reports/execucao_validada/covariate/monitoring.json). Cadeia simulador→detector testada em três seeds e UCI. |
| R06 — conceito e causalidade | Intervenção condicionada e bootstrap pareado | X/probabilidades invariáveis, aumento Brier e IC95%; par combinado/covariável. [Resultados](resultados.md), causalidade no README e [análise completa](causalidade.md). |
| R07 — operação /20% | `telemetry`, `tracking`, `pipeline`, `reporting` | [Painel](../reports/execucao_validada/index.html), logs/alertas, duração/volume/recursos e [metadados do pai e quatro filhos](evidencias_mlflow.json). Sucesso SQLite e download dos artefatos com links válidos testados. |
| R08 — governança /15% | Governança consolidada no README | Finalidade, minimização, base legal contextual, retenção proposta, direitos, revisão, vieses e incidentes; [model card](model_card.md) e auditoria agregada no painel. Não é certificação de conformidade. |
| R09 — repositório/histórico/reprodução | `uv.lock`, CI, comandos e revisões | [Verificação local](verificacao.json), [tratamento Fable](revisoes/tratamento.md), hashes e [auditoria](auditoria_final.md). Commits semânticos por bloco registrados após autorização dos hooks locais; configuração global do trabalho preservada. CI remoto tem estado próprio e não é alegado sem execução. |
| R10 — vídeo STAR /15% | [Roteiro de até 5 min](roteiro_star.md) | **Vídeo e link não produzidos**, por solicitação expressa. Roteiro não substitui atendimento do critério de gravação original. |

Comandos de reprodução estão no README. Todos os testes são executados pelo comando padrão `uv run pytest -q`; o marker `integracao` não é excluído pelo CI. Um skip em cache ausente não é declarado como execução UCI. O dataset real foi executado integralmente e seus resultados agregados estão incluídos.

A validação visual de navegador foi interrompida por limitação da ferramenta, que não conseguiu confirmar a URL. Os HTMLs foram gerados pela biblioteca real e verificados automaticamente quanto a JSON, conteúdo, links relativos e integridade; inspeção visual manual permanece recomendada.
