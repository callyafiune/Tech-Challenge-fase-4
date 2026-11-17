# Estado da implementação

O estado técnico é comprovado pelas execuções, relatórios e registros de verificação indicados abaixo.

| Componente | Resultado | Evidência |
|---|---|---|
| Dados | Base UCI de 30.000 registros, com integridade e licença identificadas. | [Dicionário](dicionario_dados.md) e manifesto da execução. |
| Contratos | Nulos, idade inválida e duplicidade bloqueados antes da inferência. | Campo `contracts` no [resumo](../reports/execucao_validada/resumo.json). |
| Modelo | HistGradientBoosting, limiar 0,30 e AUROC de validação 0,773570. | [Model card](model_card.md) e [resultados](resultados.md). |
| Drift | Quatro cenários; `limit_bal` e `pay_0` detectados pela política primária no covariável e combinado. | [Resultados](resultados.md) e relatórios Evidently. |
| Conceito simulado | Entradas e probabilidades preservadas nos pares; piora de Brier com IC95% positivo. | [Causalidade](causalidade.md). |
| Observabilidade | Eventos, recursos, oito alertas e hierarquia MLflow de um pai e quatro filhos por execução. | [Painel](../reports/execucao_validada/index.html) e [metadados MLflow](evidencias_mlflow.json). |
| Governança | Finalidade, minimização, base legal contextualizada, retenção e auditoria de equidade documentadas. | [Governança](governanca.md). |
| Docker | Execução com rede e repetição sem rede; falha esperada com cache vazio; exportação e UI verificadas. | [Guia Docker](docker.md) e [verificação](verificacao_docker.json). |
| Qualidade | 150 testes aprovados; Ruff e formatação aprovados. | [Registros do pipeline](verificacao.json) e [coleta local](validacao/docker-qualidade-final.json). |
| Apresentação | Vídeo STAR publicado, com demonstração dos relatórios, alertas e governança. | [Assistir no YouTube](https://youtu.be/0NyRf1oxfeI). |

## Execução de referência

O retrato publicado corresponde a `20261116T220412_87839641f75d`: status `sucesso`, 38,67498 segundos, 22 eventos e oito alertas. O run pai MLflow é `b987bfd1e9a848179a2bdeec3eb526fc`, com quatro filhos `FINISHED`.

O manifesto identifica 31 arquivos de fontes/configuração, com SHA-256 agregado `312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73`, vinculados à revisão `11dd2b83b57a77ceda8186d6c61b79e20e0dca35`. Os relatórios publicados contêm indicadores agregados; dados brutos, predições individuais, modelo e banco ficam fora desse retrato.

## Verificações e limites

A [captura da CLI](execucao_cli.json) registra o processo original, o código de saída e a identidade das fontes. O [índice de verificação](verificacao.json) reúne comandos, JUnit, horários e hashes. Os testes negativos cobrem adulteração de ID, estado, configuração e artefatos.

Os [pareceres técnicos](revisoes/tratamento.md) são leituras estáticas; a comprovação de execução vem dos logs, testes e artefatos. Os HTMLs têm verificações automatizadas de conteúdo, links e integridade. As medições são locais, sem promessa de desempenho ou certificação de operação de crédito.
