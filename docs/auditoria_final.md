# Auditoria técnica — confiabilidade de crédito

Avaliação dos contratos, isolamento de dados, estatística, observabilidade, privacidade e rastreabilidade do pipeline descrito no [enunciado](enunciado.md).

## Evidências examinadas

| Evidência | Conteúdo |
|---|---|
| [Execução validada](resultados.md) | Base real, métricas, cenários e limitações. |
| [Manifesto](../reports/execucao_validada/manifesto.json) | Identidade de dados, configuração, fontes e artefatos. |
| [Captura da CLI](execucao_cli.json) | Comando original, horários e código de saída zero. |
| [Verificação local](verificacao.json) | Sete comandos, 150 testes aprovados, JUnit e hashes. |
| [MLflow](evidencias_mlflow.json) | Run pai e quatro filhos finalizados, métricas e artefatos. |
| [Verificação Docker](verificacao_docker.json) | Execuções com e sem rede, falha esperada e identificação da imagem. |

## Achados tratados

| ID | Prioridade | Achado | Resultado |
|---|---|---|---|
| A01 | P1 | URIs de backend podiam expor credenciais ou metadados remotos. | Destinos não SQLite são publicados como `destino_remoto_omitido`; regressões cobrem diferentes formatos de URI. |
| A02 | P2 | Links dos relatórios de cenários não acompanhavam o HTML do run pai. | Artefatos sincronizados na árvore do pai; navegação relativa e download verificados. |
| A03 | P2 | Drift indefinido era apresentado como ausência de mudança. | Estados de amostra insuficiente e avaliação pendente são explícitos. |
| A04 | P2 | A revisão Git isolada não identificava alterações locais do código executado. | Fontes e configuração identificadas por hashes individuais e agregados. |
| A05 | P2 | URIs malformadas ainda podiam preservar partes de credenciais. | Omissão integral do destino remoto, com testes negativos específicos. |

Os achados estão tratados no retrato de referência. A integridade é conferida por bytes, configuração, ID e inventário completo de artefatos, sem depender de `git_dirty` como condição de aceite.

## Resultados e qualidade

A execução `20261116T220412_87839641f75d` concluiu com 30.000 registros, quatro cenários de 2.500 linhas, 22 eventos e oito alertas. AUROC de validação: **0,773570**; referência independente: **0,767351**. O covariável apresenta drift primário em `limit_bal` e `pay_0`.

Os contrastes pareados preservam entradas e probabilidades. O aumento de Brier é **0,347198** no conceito contra controle e **0,228136** no combinado contra covariável. A intervenção é sintética e severa; não identifica causas econômicas reais. Valores completos e intervalos estão em [resultados](resultados.md).

Logs, JUnit e hashes comprovam a verificação técnica. Os pareceres registrados são análises estáticas, complementares aos testes; seu tratamento está no [índice de revisões](revisoes/tratamento.md).

## Governança e limites

A [governança](governanca.md) distingue dados públicos de anonimização, dados pessoais de dados sensíveis, retenção proposta de obrigação legal e revisão humana recomendada de obrigação geral. O projeto é acadêmico e não constitui certificação jurídica, de equidade ou de operação real de crédito.

As auditorias por grupo usam tamanho e denominadores mínimos, com supressão complementar. Essa mitigação não comprova anonimização nem eliminação de viés. Relatórios agregados podem conter metadados locais e histogramas de categorias raras; dados privados exigem revisão de divulgação.

Os HTMLs são verificados automaticamente quanto a conteúdo, links e integridade. Inspeção visual manual: não realizada. Hashes comprovam consistência, sem substituir assinatura ou garantia de autenticidade contra alteração coordenada de todos os arquivos.

O [vídeo STAR](https://youtu.be/0NyRf1oxfeI) apresenta a demonstração técnica. A [matriz de rastreabilidade](matriz_rastreabilidade.md) relaciona os requisitos aos artefatos disponíveis.
