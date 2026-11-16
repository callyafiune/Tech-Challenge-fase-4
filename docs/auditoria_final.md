# Auditoria final — confiabilidade de crédito

Auditoria realizada em 16/11/2026, com esforço solicitado **xhigh** e velocidade **standard**. O escopo é o Tech Challenge acadêmico, conforme [enunciado](enunciado.md) e instrução de entregar somente roteiro STAR. Não constitui certificação de operação de crédito ou parecer jurídico.

## Escopo e critério de conclusão

Foram lidos todos os módulos de `src/credito_monitorado`, os testes, a configuração, o workflow, os scripts, README, cards e documentação causal. Também foram lidos os pareceres Fable 00, 01, 01b, 02, 02b, 03, 03b, 03c, 03d, 03e, 04 e 04b e seus metadados disponíveis. Serena não estava disponível; a inspeção usou leitura de arquivos, buscas e verificações locais.

A evidência real examinada inicialmente foi `artifacts/20261116T210604_8c2119de557d/resumo.json`. A auditoria integral conferiu **`20261116T215129_2bee07608434`**, com **150 testes passando** nos registros posteriores. Após o versionamento, o principal produziu o retrato limpo atual **`20261116T220412_87839641f75d`**, na revisão **`11dd2b83b57a77ceda8186d6c61b79e20e0dca35`**, com `git_dirty=false`. Esta atualização é documental: não repetiu testes, lint ou pipeline. Os 31 arquivos e o hash agregado `312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73` permanecem os mesmos; a nova suíte do principal estava em andamento, sem resultado antecipado neste registro.

Nenhum código, teste, README, hook ou commit foi alterado pelo auditor. Foram atualizados somente arquitetura, plano, progresso e este parecer.

## Achados por prioridade

**P0:** nenhum defeito dessa prioridade foi demonstrado.

| ID | Prioridade / requisito | Defeito concreto observado | Situação e aceite |
|---|---|---|---|
| A01 | P1 — privacidade/R08 | `pipeline._safe_tracking_uri` removia credenciais somente de HTTP/HTTPS. Uma URI sintética PostgreSQL com sentinela retornava a sentinela, que seria persistida em resumo/manifesto e anexada ao MLflow. | Corrigido durante a auditoria. A reprodução passou a confirmar ausência da sentinela; testes cobrem HTTP, HTTPS, PostgreSQL, MySQL e SQLite. Não houve uso ou exposição de credencial real neste teste. |
| A02 | P2 — observabilidade/R07 | O `index.html` anexado ao run pai apontava para `<cenario>/evidently.html`, mas os relatórios existiam apenas nos runs filhos. Baixar o HTML do pai quebrava a navegação relativa. | Corrigido por `tracking.sync_tracking_artifacts`, com integração SQLite/download e checagem dos links. Na execução UCI final foram conferidos 16 links locais na árvore do pai, sem quebra. |
| A03 | P2 — interpretação estatística/R05–R07 | `reporting.render_summary` convertia `drift=None` em “não” e lista vazia de atributos em “nenhum”, ocultando `insufficient_sample`. A reprodução usou somente resumo sintético derivado dos agregados. | Corrigido durante a auditoria: nova reprodução confirma “amostra insuficiente” e “pendente”. O lote real padrão de 2.500 linhas não foi afetado por esse caminho. |
| A04 | P2 — proveniência/R09 | A execução histórica identifica o `Initial commit`, sem indicador de árvore suja nem fingerprint do código executado. Esse commit não contém a implementação auditada. | Corrigido por fingerprint explícita. Os 31 arquivos do retrato conferido também são idênticos em bytes aos blobs do commit técnico `5152b36`; a pendência de hooks foi resolvida por autorização e o histórico semântico técnico existe. |
| A05 | P2 — metadados/privacidade | A revisão 03c apontou que uma URI ambígua como `postgresql://usuario:12/ss@host/banco` podia deixar `usuario` como hostname em `_safe_tracking_uri`. | Corrigido na versão final: qualquer destino não SQLite é publicado como a constante `destino_remoto_omitido`, sem reaproveitar partes da entrada. A correção foi lida e consta das fontes da execução conferida; regressões adicionais integram os 150 testes registrados. Nenhuma credencial real foi utilizada nesta auditoria. |

A01–A05 foram fechados por inspeção e pelas evidências correspondentes. Não há P0/P1/P2 aberto demonstrado no retrato conferido. O histórico técnico foi confirmado separadamente após a autorização específica do usuário, sem inferi-lo apenas do êxito do pipeline.

O ponto de consistência encaminhado ao implementador também foi fechado: duração, memória e quantidade de alertas do pai MLflow correspondem exatamente ao resumo final. A duração inclui a sincronização medida e exclui a cópia final dos snapshots; o próprio resumo explicita esse escopo.

## Evidência real conferida

Na execução `20261116T210604_8c2119de557d`, o status é `sucesso`, a duração registrada é 31,089319 segundos e as 16 entradas de `artifacts_sha256` do manifesto conferem com os arquivos locais. A inspeção SQLite em modo somente leitura confirmou um run pai e quatro filhos `FINISHED`; no pai, AUROC 0,7735701331, oito alertas e duração 31,089319 coincidem com o resumo.

| Conjunto / cenário | Registros | AUROC | Brier | Drift primário de X |
|---|---:|---:|---:|---|
| Validação | 4.500 | 0,773570 | 0,138121 | Não se aplica |
| Referência holdout | 4.500 | 0,767351 | 0,137971 | Não se aplica |
| Controle | 2.500 | 0,782513 | 0,130344 | Nenhum |
| Covariável | 2.500 | 0,796500 | 0,159724 | `limit_bal`, `pay_0` |
| Conceito simulado | 2.500 | 0,407339 | 0,477542 | Nenhum |
| Combinado | 2.500 | 0,464895 | 0,387860 | `limit_bal`, `pay_0` |

No covariável, `limit_bal` apresenta KS D=0,181511 e p BH=1,393176×10⁻⁴⁵; `pay_0` apresenta PSI=0,205308, acima do corte 0,20. O sinal de `pay_0` é próximo ao corte e vale para o experimento fixado; não garante detecção em qualquer amostra futura. O controle tem D=0,020089 em limite e PSI=0,008373 em atraso, sem alertas primários nessas colunas.

No par conceito/controle, X e probabilidades são idênticos, o aumento pareado de Brier é 0,347198 e o IC95% bootstrap é [0,327206; 0,367646]. No par combinado/covariável, o aumento é 0,228136, IC95% [0,211196; 0,244529]. A preservação de X torna a interpretação coerente com a intervenção conhecida nos rótulos; a identificação não vem somente da queda de AUROC.

O lote inválido foi bloqueado integralmente: nulo, idade, duplicidade e combinação são registrados como rejeitados. A execução histórica contém 18 eventos e oito alertas. A auditoria de grupos em referência tem no mínimo 429 registros por faixa etária e 1.802 por sexo nessa execução; os gaps de aprovação são descritivos, sem certificado de equidade.

## Retrato limpo atual e comprovações anteriores

A execução atual **`20261116T220412_87839641f75d`**, informada pelo principal após o commit documental `11dd2b8`, terminou com `sucesso`, **38,67498 segundos**, **22 eventos** e **oito alertas**. O pai MLflow é **`b987bfd1e9a848179a2bdeec3eb526fc`**, com quatro filhos `FINISHED`. A revisão registrada contém o código executado e `git_dirty=false` descreve o estado no início dessa execução. O snapshot atual é `reports/execucao_validada`. As comprovações detalhadas abaixo pertencem à auditoria anterior dos mesmos bytes de código; os novos metadados e a nova rodada de verificação serão consolidados pelo principal.

A execução **`20261116T215129_2bee07608434`** terminou com `sucesso`, **22 eventos**, **oito alertas** e **23,767508 segundos**, sem falhas inesperadas. O controle positivo do contrato foi validado; as quatro variantes inválidas foram rejeitadas. A ausência de inferência nesse ramo é explicitamente identificada como garantia do fluxo, sem alegar contador instrumentado.

| Verificação final | Resultado observado |
|---|---|
| Identidade das fontes | Os 31 arquivos de código/testes/scripts/configuração/lock/workflow/versão Python/atributos Git têm bytes correspondentes aos hashes registrados. O conjunto atual também é idêntico ao registrado. |
| Hash agregado | `312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73`, recalculado e confirmado. |
| Estado Git da execução conferida | `git_dirty=true`, com HEAD inicial declarado, preservado como fato histórico. Posteriormente, os 31 arquivos foram comparados aos blobs de `5152b36`, sem divergência. |
| Manifesto local | 17 hashes conferidos, inclusive `index.html`; identidade de fontes igual à do resumo. |
| Snapshot público | `reports/execucao_validada`: 17 arquivos inventariados com hashes corretos e bytes iguais à origem, mais `publicacao.json`, totalizando 18 arquivos. |
| Exclusões da publicação | Nenhum arquivo bruto, CSV/Parquet, ZIP/XLS, modelo joblib/pickle ou banco foi incluído. O inventário explicita as exclusões. |
| Links HTML | 32 links relativos conferidos entre origem/snapshot e 16 na árvore de observabilidade do pai MLflow, sem arquivos faltantes. Links externos não foram tratados como arquivos locais. |
| Aviso Evidently | Um banner por HTML de cenário, como filho do `body`, fora de scripts; nenhum `script src` externo nesses quatro relatórios. É validação estrutural automatizada. |
| MLflow | Pai `a3cff0b470994809b9e85c89b001c5c5` e quatro filhos `FINISHED`. A hierarquia foi conferida pela tag `mlflow.parentRunId` na consulta SQLite e no JSON exportado, com experimento, horários, nomes e artefatos. |
| Métricas do pai | Duração 23,767508 s, RSS máximo amostrado 369,18 MiB e oito alertas, exatamente iguais ao resumo local. |
| Artefatos do pai | `resumo.json` e `manifesto.json` idênticos em bytes aos locais; eventos correspondentes. |
| Novos sinais | Evidently `success` nos quatro cenários; score drift em covariável/combinado e ausente em controle/conceito; janelas simuladas T0–T3 registradas. |

Os hashes de dataset, configuração e modelo e todas as métricas supervisionadas dos cenários permaneceram iguais aos da execução histórica; os números estatísticos da tabela anterior continuam válidos. A melhoria de observabilidade não alterou o modelo ou fabricou um novo resultado de drift. O snapshot final e os documentos [resultados](resultados.md), [matriz](matriz_rastreabilidade.md) e [tratamento](revisoes/tratamento.md) foram inspecionados e remetem à execução correta. Os acentos de `resultados.md` foram conferidos em UTF-8 após correção da gravação inicial pelo implementador.

O [registro de verificação](verificacao.json) contém sete comandos com horários sequenciais, código zero, stdout/stderr literal e hash por log. Os sete arquivos foram comparados em bytes com os hashes e o texto registrados, sem divergência. O log do pytest informa **150 passed, 11 warnings in 48.79s**; o [JUnit](validacao/pytest.xml) confirma 150 testes, zero falhas, zero erros e zero skips. A verificação ocorreu depois da execução real, sem sobreposição dos horários. O hash do manifesto registrado é `22edfa15f16d4d3c87fa6de37cffee220e9759d65ab011a369f8e851045ef8b0` e confere com o arquivo.

O bloco `execucao_real` identifica expressamente o status como derivado do resumo e o comando/código da CLI original como não capturados. Não existe mais código zero atribuído a um processo que o verificador não observou. O comando para reprodução é uma referência, separada dos sete processos efetivamente capturados. `validate_execution` foi lido: valida diretório/ID, configuração atual, correspondência resumo/manifesto, conjunto e hashes de todos os artefatos e identidade por bytes, sem condicionar a comparação a `git_dirty`. O registro informa `current_source_sha256` igual ao salvo e `source_matches=true`. Testes negativos específicos do helper constam da suíte final; não foram reexecutados pelo auditor.

A captura independente [execucao_cli.json](execucao_cli.json) e o [log original da CLI](validacao/00-pipeline-cli.log) confirmam comando executado, código **0**, ID e hash das fontes correspondentes. Os bytes do log conferem tanto com `saida_literal` quanto com SHA-256 `c7f7139d287ac635294be379c39b6acc1c271536e796168c90ba9f60b2b91707`. A captura foi encerrada antes do início dos sete comandos de verificação. Não se confunde essa observação independente com o bloco derivado do verificador.

Para tornar explícita a inspeção desta rodada, o JUnit conferido tem SHA-256 `773048a557d614dc8db86e47a3d5e4fca2c6da921fdaa467b6267735afd0c5e1` e `evidencias_mlflow.json` tem SHA-256 `1de6e76074d33940015408db74ab1dd42fe473791a97475e4c522fa6905443ca`. Os hashes adicionais do registro também foram conferidos. O JSON MLflow corresponde aos IDs, estados e métricas conferidos no SQLite, incluindo a associação por `mlflow.parentRunId`, experimento, horários, nomes e lista de artefatos.

**Limite de apresentação:** a ferramenta de navegador foi interrompida por não confirmar a URL. Esta auditoria registra somente validação automatizada de estrutura, conteúdo, links, JSON e integridade; não alega inspeção visual manual ou aprovação da renderização interativa.

## Confronto de requisitos com implementação

| Requisito | Evidência examinada | Conclusão desta auditoria |
|---|---|---|
| Base financeira binária >= 5.000 | Pins ZIP/XLS em `data.py`, manifesto e 30.000 linhas normalizadas | Atendido na execução real; sem substituição por base sintética. |
| Baseline simples e separação | `model.train_baseline`, `data.split_dataset`, hashes e métricas | Fit somente em treino; 15.000/4.500/4.500/6.000. Referência holdout é uma escolha conservadora que representa a distribuição do treino sem reutilizar os mesmos registros. |
| Pelo menos três regras rígidas e bloqueio | `contracts.validate_batch`, testes de domínio e demonstração | Atendido. Tipos, finitude, idade 19–100 e ID único são exemplos; sem coerção ou remoção silenciosa. |
| Pelo menos duas variáveis em drift | `drift.build_scenarios`, `compute_drift`, scores reais e Evidently | Atendido no experimento fixado. Seleção consulta somente X e conserva os rótulos originais. |
| Conceito e causalidade | `monitoring.compare_concept`, hashes e pares | Atendido como contrafactual sintético severo. Não é demonstração de uma mudança econômica observada. |
| Uso efetivo do Evidently/HTML | Quatro HTML/JSON gerados e adapter da API 0.7 | Atendido. Sua decisão bruta é complementar à política própria BH/efeito; banner, estados e JSON primário constam no retrato final. |
| Logs, métricas operacionais e tracking | Telemetry, resumo, SQLite com pai/filhos e relatório local | Atendido no fluxo real final; links e métricas foram conferidos. |
| Governança consolidada no README | Finalidade, base contextualizada, retenção, direitos, vieses e incidentes | Atendido como plano acadêmico contextualizado, com limitações de implementação declaradas. |
| Histórico semântico organizado | Histórico e configuração local autorizada | Resolvido: `1ec1062`, `734d66e`, `2b8c3bc`, `5152b36` e documentação em `11dd2b8`. O retrato limpo atual registra essa revisão; a atualização de evidência será consolidada pelo principal. Push não é declarado. |
| Vídeo STAR de até cinco minutos | `docs/roteiro_star.md` | Roteiro atende à instrução do usuário. Vídeo/link exigidos no enunciado continuam ausentes, por exclusão expressa do escopo autorizado; não atribuir cumprimento integral desse critério. |

## Estatística, vazamento e privacidade

Não foi identificado ajuste do modelo usando referência ou produção: `fit` recebe somente `train[FEATURES]`, com `early_stopping=False`. O limiar 0,30 e os hiperparâmetros são políticas acadêmicas predefinidas, não uma política de custo financeiro validada. ID, alvo, sexo, escolaridade e estado civil ficam fora dos preditores; idade permanece. A exclusão por ID não prova independência completa dos perfis repetidos da fonte, limitação corretamente reconhecida no dicionário.

BH está implementado corretamente na família de contínuas; os estados discretos de pagamento usam PSI. O PSI contínuo usa bins fixados pela referência, extremos abertos e tratamento de referência constante. O bootstrap reamostra a diferença de perdas nos pares correspondentes. Um intervalo positivo para a média com estimativa >=0,05 não demonstra que todo o intervalo está acima de 0,05; esse não é o critério especificado. Os alertas pontuais de desempenho servem à investigação e não provam conceito no mundo real.

Seleção apenas por X sustenta a hipótese construtiva de preservação do mecanismo condicional, sem provar essa invariância empiricamente. Quatro cenários estáticos e uma inversão severa não estimam taxa de falsos alarmes, poder contra drift pequeno ou evolução de safras reais. A sequência temporal é simulada. Essas limitações são aceitáveis para a demonstração e estão documentadas; não foi exigida curva de sensibilidade, produção contínua ou certificação setorial adicional.

O README distingue dados públicos de anonimização, dados pessoais de dados sensíveis, retenção proposta de obrigação legal e revisão humana recomendada de obrigação geral do art. 20. A proteção do crédito do art. 7º, X é contextualizada para a fintech hipotética; não deve ser tomada como autorização automática para qualquer finalidade acadêmica ou acessória. A [LGPD atualizada, fonte oficial da Câmara](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html) foi consultada nesta auditoria. Não foram identificados nomes, CPF, IDs de clientes ou `failure_cases` nos logs agregados examinados. Não foi tentada reidentificação.

Supressão apenas por tamanho total >=30 não resolveria sozinha inferência por diferenças ou denominadores pequenos de TPR/FPR. A versão final acrescenta supressão complementar por dimensão e mínimo nos denominadores específicos; isso é mitigação, não prova de anonimização ou justiça. O snapshot foi inspecionado e não inclui modelos/bancos/brutos. Não há afirmação de expurgo automático, autenticação de produção ou criptografia adicional implementados.

## Revisões e verificações finais a confirmar

Os metadados dos pareceres 00, 01, 01b, 02 e 03 informam `claude-fable-5-2`, velocidade `standard` e `is_error=false`. Os escopos contêm respectivamente 4, 7, 8, 6 e 11 arquivos; nenhum desses pareceres isoladamente equivale a uma auditoria executada de todo o projeto. Alegações históricas sobre arquivos ausentes no pacote não foram repetidas como defeitos do repositório completo.

A ausência de `pipeline.py`, `data.py` ou `cli.py` no pacote 02b explica ressalvas sobre regras não pareadas, separação completa e sanitização na borda. No repositório completo, `_scenario_alerts` usa os limiares de AUROC/Brier como sinais exploratórios; `split_dataset` e a guarda da integração verificam exclusão; CLI/telemetria sanitizam a saída persistida. Essas ressalvas são adjudicação de escopo, não novos defeitos demonstrados. O contraste pareado continua restrito à intervenção conhecida.

As rodadas 03b/04 reconheceram correções e coerência numérica; os problemas de acentuação, roteiro e documentação causal foram tratados. As rodadas 03c/04b acrescentaram A05 e ressalvas de proveniência, fechadas na versão atual. Contagens antigas de testes nesses pareceres são históricas; o registro final é de 150. A diferença de escopo do Ruff está comprovada no sétimo log: o formatador processa também Markdown, enquanto o lint tem inventário próprio. Não há código Python oculto inferido dos contadores. A identidade da execução é definida pelos 31 arquivos explicitamente enumerados.

A omissão integral de metadados remotos e o fortalecimento do verificador constam das fontes da execução final. A rodada **03d** confirmou os três itens da 03c e apontou uma lacuna importante na discriminação dos testes negativos. A rodada **03e**, lida nesta auditoria, julgou **CORRIGIDOS** os casos de ID, status e escape, sem crítico ou importante aberto nesse escopo. Os hashes dos dois arquivos revisados por 03e conferem com os bytes atuais. O JUnit contém os 12 casos do helper sem falhas, e a suíte completa correspondente tem 150 testes aprovados. Fable realizou leitura estática; a execução dos testes é comprovada pelos registros separados.

Os casos agora isolam os guards: cópia íntegra em diretório com outro ID; status de falha coerente em resumo/manifesto com hashes válidos; e espião que impede leitura do arquivo externo antes da rejeição de escape. Não foi necessário alterar o helper nessa última correção de cobertura.

Ressalvas menores aceitas no contexto acadêmico: consistência por hashes não é assinatura ou autenticidade contra quem possa forjar toda a cadeia; o uso documentado é checkout uv/editável, e não instalação arbitrária; logs verbosos incluem caminhos de perfil local, explicitados como metadados de execução; o espião acompanha a implementação atual com `Path.read_bytes`; ID/status compartilham mensagem e sua discriminação vem das fixtures. As demais fragilidades menores de leitura/configuração e evolução futura foram registradas no tratamento, sem alegar garantia implementada. Não se reabriu o exercício como certificação de produção, calibração sequencial ou prova de equidade.

Rodadas anteriores foram observadas pelo auditor; a rodada final usa os registros automáticos acima, com **150 testes passando, 11 warnings e 48,79 s**, sem executar os testes novamente. Os warnings são de dependências e não invalidaram a execução. `.gitattributes` preserva os bytes que identificam as fontes; o atributo localizado de `docs/validacao` preserva o espaçamento literal dos logs. Os comandos de whitespace final têm código zero e logs vazios conferidos. A contagem do formatter é reproduzida como saída da ferramenta, sem tratá-la como inventário de arquivos Python.

- [x] Conferir os sete logs literais/JUnit da rodada final e 150 testes, com identidade das fontes correspondente.
- [x] Conferir nova execução UCI, source identity, invariantes, métricas, score drift, Evidently e artefatos/links locais e no MLflow.
- [x] Conferir correspondência de duração/recursos/alertas entre métricas do pai e resumo final.
- [x] Conferir snapshot `reports/execucao_validada`, inventário e ausência de dados/modelos/banco.
- [x] Conferir resultados, matriz e tratamento das revisões disponíveis no fechamento.
- [x] Ler as rodadas finais 03b/04 e 03c/04b e separar ressalvas atuais de observações históricas ou de escopo.
- [x] Fechar A05 e os resíduos de integridade do verificador com código/evidência atuais.
- [x] Incorporar 03d/03e e fechar a ressalva importante de cobertura com os mesmos bytes e evidências finais.
- [x] Registrar a autorização específica para hooks locais e conferir os quatro commits técnicos, preservando a ocorrência histórica do bloqueio.

O parecer fecha A01–A05, os resíduos do verificador e a ressalva importante de cobertura, com menores aceitos. As rejeições anteriores nas duas branches são histórico: o usuário autorizou hooks locais apenas neste projeto acadêmico, preservando o global corporativo. O principal configurou `core.hooksPath=.git/hooks`, criou os quatro commits técnicos e o documental `11dd2b8`. O novo retrato limpo registra essa revisão e os mesmos 31 arquivos. A atualização das evidências será consolidada pelo principal; nenhum push é alegado nesta auditoria. Esta auditoria valida execução local; o CI é consultável na aba Actions e tem estado autônomo, sem aprovação antecipada. Inspeção visual manual não foi realizada e vídeo/link permanecem fora do escopo autorizado; isso não constitui certificação de operação real.

## Consolidação observada pelo executor após o versionamento

O verificador automático concluiu sobre `220412` e os mesmos bytes: **150 testes passaram, 11 avisos, 126,89 segundos**, sem falhas ou skips. Os sete comandos terminaram com código zero, entre `2026-11-16T22:09:01Z` e `2026-11-16T22:11:14Z`, depois da execução da CLI. `current_source_sha256` coincide com o manifesto e `source_matches=true`. Log literal, JUnit e metadados MLflow atualizados estão vinculados em `docs/verificacao.json`. Este parágrafo registra o resultado do executor; o auditor não reexecutou a suíte.
