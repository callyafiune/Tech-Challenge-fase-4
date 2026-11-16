# Registro de progresso

Registro iniciado em 16/11/2026 e atualizado durante a auditoria final. Os estados abaixo distinguem a execução real observada das correções e verificações ainda em andamento; não substituem resultados por intenções.

## Base e instruções

- Workspace: `C:\estudos\Tech-Challenge-fase-4`.
- Branch de trabalho atual: `feature/observabilidade-credito`.
- Commit inicial observado por `git log`: `22313dd90a88bded39fa6865493c58d5ee692abf` (`Initial commit`).
- Enunciado: `C:\estudos\MLET-Tech-Challenge-Fase-4.md`, lido em UTF-8.
- Serena não estava disponível; navegação realizada por arquivos e ferramentas de texto. Os `AGENTS.md` global e local foram considerados.
- Execução ponta a ponta solicitada. O usuário autorizou especificamente hooks locais neste repositório acadêmico, preservando a configuração corporativa global. Produzir roteiro STAR; gravação de vídeo e link ficam fora do escopo.

## Decisões técnicas consolidadas

1. Usar Python 3.11, uv e `uv.lock`, layout `src/credito_monitorado`, `params.yaml` na raiz, Pandera, scikit-learn, Evidently e MLflow.
2. Usar UCI Default of Credit Card Clients, com 30.000 registros, licença atribuída e manifesto de proveniência/hash.
3. Separar IDs em treino 15.000, validação 4.500, referência holdout 4.500 e pool de produção 6.000; seed 42. Somente treino ajusta o modelo.
4. Usar `HistGradientBoostingClassifier` (`max_iter=150`, `learning_rate=0.08`, `max_leaf_nodes=15`) e limiar fixo 0,30. Excluir identificador, sexo, escolaridade, estado civil e alvo dos preditores; manter demografia apenas para auditoria agregada.
5. Gerar controle, covariável, conceito e combinado com 2.500 linhas por lote. Seleção covariável sem reposição usa apenas X: pesos 3 para limite baixo e 4 para atraso em `pay_0`. Conceito conserva X do controle e inverte alvo com probabilidade 0,8 somente em `pay_0 <= 0`.
6. Medir KS com BH a 5% e efeito mínimo 0,10, PSI >= 0,20 com epsilon 1e-6; exigir no mínimo 200 linhas. Conceito usa aumento pareado de Brier >= 0,05 e bootstrap de 500 reamostragens com IC95% inferior > 0; queda de AUROC de 0,05 é sinal complementar.
7. Consolidar HTML, logs JSONL, alertas e runs MLflow; limites operacionais de 120 segundos por estágio e RSS de 2.048 MB.
8. Tratar cenários como intervenções sintéticas; documentar hipóteses de seleção e não alegar inferência causal macroeconômica ou conformidade legal automática.

## Esforços e revisão

| Tipo de trabalho | Esforço solicitado |
|---|---|
| Arquitetura e auditoria | xhigh |
| Pipelines e modelo | high |
| Estatística | high |
| Testes e refatorações simples | medium |
| Depuração difícil | xhigh |

Velocidade solicitada: **standard**, sem modo fast. Registrar a configuração efetiva quando o runtime expuser esse controle; não afirmar que um parâmetro não configurável foi aplicado. Na preparação, o agente de arquitetura/plano trabalhou apenas em documentação e nas duas chaves estatísticas autorizadas de `params.yaml`, sem instalar dependências, implementar módulos ou criar commits. Na auditoria, leu implementação/testes/evidências, executou verificações e atualizou somente documentação.

Cada bloco recebe revisão adversarial pelo Claude Code com `--model fable`, conforme `AGENTS.md`. Pareceres 00, 01, 01b, 02 e 03 foram lidos; seus JSON registram `claude-fable-5-2`, `standard` e ausência de erro. O tratamento final das ressalvas permanece em consolidação. A auditoria final xhigh está registrada em [auditoria_final.md](auditoria_final.md).

## Estado dos blocos

| Bloco | Estado neste registro | Próxima evidência necessária |
|---|---|---|
| Arquitetura e planejamento | Escritos; interfaces/contratos alinhados | Preservar consistência após eventuais achados das revisões finais |
| Dados, contratos e modelo | Nova execução UCI real conferida | Nenhuma pendência técnica demonstrada nesta auditoria |
| Drift e estatística | Dois atributos em drift e conceito pareado comprovados no retrato conferido | Limites de sensibilidade/causalidade declarados |
| Observabilidade | Links, hashes, métricas e pai+quatro filhos conferidos | URI remota omitida integralmente; nenhuma ressalva técnica aberta nesta auditoria |
| Documentação e governança finais | Resultados, matriz, snapshot, README/cards e tratamento inspecionados | Verificações finais refletidas; vídeo/visual/CI remoto explicitados |
| Revisão adversarial e auditoria final | A01–A05, helper e ressalva importante de cobertura fechados | 03d/03e incorporados; menores aceitos e documentados |
| Histórico semântico | Resolvido por autorização específica | Quatro commits técnicos e documentação `11dd2b8`; evidência do retrato limpo em consolidação |

## Verificação desta preparação

Na preparação, foram criados `docs/arquitetura.md` e `docs/plano_implementacao.md`, com matriz R01–R10, interfaces, blocos e critérios verificáveis. A leitura UTF-8 estrita e a checagem explícita de whitespace final/caracteres de substituição passaram. `git diff --check` não apontou erros nos arquivos rastreados naquele momento. Nessa etapa inicial o agente ainda não havia executado testes de código nem declarado resultados de modelo/drift; as verificações posteriores estão registradas abaixo.

## Execução real e auditoria

A execução `20261116T210604_8c2119de557d` foi examinada em disco e no SQLite local: status `sucesso`, 30.000 registros, quatro cenários de 2.500, AUROC de validação 0,773570, oito alertas e 31,089319 segundos. Os 16 hashes de artefatos conferem; o run pai e quatro filhos estão `FINISHED`. O covariável detecta `limit_bal` e `pay_0`, com KS D=0,181511 e PSI=0,205308 respectivamente; o controle não registra drift primário. Conceito aumenta Brier em 0,347198 com IC95% [0,327206; 0,367646], preservando X e probabilidades. O combinado usa o par covariável, com aumento 0,228136 e IC95% [0,211196; 0,244529].

Rodadas intermediárias de testes e de observabilidade foram acompanhadas pelo auditor, incluindo SQLite real, download/links dos artefatos e preservação do JSON primário sob falha do Evidently. O registro final de referência é de **150 testes passando**, detalhado abaixo; contagens históricas não substituem a verificação da versão correspondente.

Foram reproduzidos e encaminhados três achados: URI de backend não HTTP podia divulgar userinfo/query; links de cenários estavam ausentes no HTML anexado ao pai MLflow; drift indefinido era exibido como ausência. As correções foram lidas, as reproduções de URI/estado de amostra e o teste de download/links no SQLite passaram. A consolidação UCI ocorreu na execução descrita abaixo. O código também passou a registrar árvore suja e hashes das fontes, para não atribuir código não commitado ao commit inicial. A revisão 03c acrescentou A05, caso residual de URI ambígua, fechado por omissão integral do destino remoto.

A pendência intermediária de executar novamente e exportar evidências foi resolvida no fechamento a seguir. O hook corporativo bloqueou a criação de commits e foi encaminhado ao usuário pelo agente principal; este agente não alterou o hook nem criou commits. Vídeo/link permanecem fora do escopo autorizado; o roteiro está disponível.

## Fechamento técnico do retrato final

A execução **`20261116T215129_2bee07608434`** e o snapshot `reports/execucao_validada` foram conferidos: sucesso, 22 eventos, oito alertas, 23,767508 segundos e RSS máximo amostrado 369,18 MiB. O pai MLflow **`a3cff0b470994809b9e85c89b001c5c5`** e quatro filhos estão `FINISHED`; duração, memória e quantidade de alertas são idênticas às do resumo. Os bytes de resumo e manifesto anexados ao pai correspondem aos arquivos locais. A hierarquia foi confirmada no SQLite e no JSON exportado por `mlflow.parentRunId`, com experimento, horários, nomes e artefatos.

O hash agregado **`312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73`** foi recalculado. Os 31 arquivos conferidos coincidem com o conjunto e os hashes registrados; `git_dirty=true` descreve o estado histórico daquela execução. Após a autorização, os mesmos 31 arquivos foram comparados aos blobs do commit `5152b36`, sem divergência. Os 17 hashes do manifesto e os 17 do inventário público conferem; as cópias são idênticas à origem. O snapshot tem 18 arquivos, incluindo o inventário, sem base bruta, predições individuais, modelo ou banco.

O principal adicionou `.gitattributes` para preservar bytes de fontes/evidências entre plataformas. As verificações próprias anteriores de whitespace passaram, e os registros finais dos dois comandos têm código zero. O plano foi marcado com os trabalhos efetivamente verificados; os commits técnicos agora estão concluídos, e a inspeção visual manual permanece pendente.

Foram conferidos 32 links relativos nos HTMLs de origem/snapshot e 16 na árvore de observabilidade do pai MLflow, sem faltantes. Os quatro HTMLs Evidently têm um banner de política no corpo real, fora de scripts, e nenhum script externo por `src`. A validação é automatizada: a ferramenta de navegador foi interrompida por não confirmar a URL, portanto não houve inspeção visual manual. Os novos sinais de score, estados Evidently e janelas T0–T3 constam na execução.

Dataset, configuração, modelo e métricas supervisionadas permaneceram iguais à execução histórica. Resultados/matriz/tratamento foram inspecionados; o problema inicial de acentuação de `resultados.md` foi corrigido por gravação UTF-8 direta. O [registro automático](verificacao.json) contém sete comandos sequenciais com códigos zero e logs literais. Seus bytes e hashes foram conferidos; o log e o JUnit confirmam **150 testes passando, 11 warnings e 48,79 segundos**, sem erros/falhas/skips. O auditor não repetiu testes, lint ou pipeline nessa rodada.

A [captura independente da CLI](execucao_cli.json) registra o comando original, saída literal e código zero. O log `docs/validacao/00-pipeline-cli.log` confere em bytes e SHA-256 `c7f7139d287ac635294be379c39b6acc1c271536e796168c90ba9f60b2b91707`; ID e hash das fontes correspondem à execução final. Os sete comandos do verificador começaram depois dessa captura. O bloco derivado do verificador continua identificado honestamente como tal, separado da captura original.

O helper `validate_execution` verifica caminho/ID, configuração, correspondência de metadados, todos os hashes e inventário completo dos artefatos e identidade das fontes por bytes. A comparação ignora o estado de staging; `current_source_sha256` coincide com o salvo e `source_matches=true`. O bloco `execucao_real` identifica expressamente status derivado e comando/código da CLI original não capturados, sem fabricar um exit zero. Os hashes de JUnit/MLflow integram o registro, e os testes negativos do helper pertencem à suíte final.

As ressalvas 02b sobre módulos ausentes foram confrontadas com o repositório completo: alertas não pareados existem em `pipeline._scenario_alerts`, separação é conferida em dados/integração e a borda preserva erros sanitizados. São limites do pacote revisado, não defeitos finais inferidos. Rodadas 03b/04 reconheceram correções e números; 03c/04b acrescentaram A05 e limites do verificador, fechados na versão atual. Contagens antigas desses pareceres são históricas; o retrato final registra 150 testes.

A diferença de escopo do Ruff está comprovada no sétimo log: o formatador processa também Markdown, enquanto o lint mantém seu inventário próprio. Não se confunde esse contador com as 31 fontes identificadas. O atributo localizado em `docs/validacao` preserva os bytes dos logs de dependências. O destino remoto é a constante `destino_remoto_omitido`; somente o caminho SQLite local é preservado. Essas correções constam dos bytes da execução final, não são intenções futuras.

03d confirmou os três itens de integridade da 03c e deixou uma ressalva importante sobre fixtures negativas. 03e julgou **CORRIGIDOS** os três casos de ID/status/escape, sem crítico ou importante nesse escopo. Os hashes dos dois arquivos revisados por 03e conferem com os bytes atuais; os 12 testes do helper estão no JUnit final sem falhas. O helper permaneceu inalterado nessa última correção: mudaram somente as fixtures para isolar os guards.

Menores aceitos e documentados incluem consistência por hashes sem assinatura/autenticidade adversarial, uso em checkout uv/editável, caminhos de perfil local nos logs verbose e acoplamento do espião à leitura atual por `Path.read_bytes`, além das mensagens compartilhadas de ID/status. Não são apresentados como garantias resolvidas ou certificação de produção. A revisão Fable é estática; a evidência de execução está nos logs/JUnit correspondentes.

Os perfis de qualidade de código e das evidências auditadas estão fechados. As rejeições do hook nas duas branches ocorreram antes da autorização específica e não representam o estado atual. O usuário autorizou hooks locais neste projeto acadêmico; o principal configurou `core.hooksPath=.git/hooks` somente no repositório, mantendo o global corporativo intacto. Os quatro commits técnicos foram seguidos pelo documental `11dd2b83b57a77ceda8186d6c61b79e20e0dca35`. Não se alega push. Esta auditoria valida execução local; o CI é consultável na aba Actions e tem estado autônomo. Inspeção visual manual não foi realizada; o roteiro, sem gravação de vídeo, é contíguo até 4:50.

## Atualização após versionamento limpo

O principal produziu **`20261116T220412_87839641f75d`**, agora no snapshot atual, com `git_revision=11dd2b83b57a77ceda8186d6c61b79e20e0dca35` e **`git_dirty=false`**. O código permaneceu inalterado: 31 fontes, SHA agregado `312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73`. A execução registrou **38,67498 segundos**, **22 eventos**, **oito alertas** e pai MLflow **`b987bfd1e9a848179a2bdeec3eb526fc`**, com quatro filhos `FINISHED`.

Esta foi uma atualização documental baseada nos metadados encaminhados pelo principal, sem novos checks, testes ou pipeline pelo auditor. A suíte anterior de 150 testes dos mesmos bytes continua preservada como anterior; o principal ainda consolidará o resultado da nova verificação e a atualização das evidências. O CI permanece independente e não é declarado aprovado antes da consulta ao estado real na aba Actions.

## Consolidação final pelo executor

A nova verificação sobre `220412`, após o commit `11dd2b8`, encerrou com **150 testes passando, 11 avisos e 126,89 segundos**, sem skips. Os sete comandos deram código zero; os registros entre 22:09:01 e 22:11:14 UTC são posteriores à CLI. Fontes e configuração coincidem com o manifesto, incluindo os 31 hashes, e os arquivos das evidências foram revalidados. Os commits técnicos e a documentação estão registrados por bloco. A atualização do retrato pós-versionamento será registrada em commit documental próprio; o estado remoto é consultável no GitHub e não é inferido do sucesso local.
