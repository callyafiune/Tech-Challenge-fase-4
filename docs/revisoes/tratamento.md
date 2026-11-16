# Tratamento das revisões adversariais

Os pareceres numerados são históricos preservados do pacote enviado naquele momento. Cada JSON registra modelo resolvido, sessão e SHA-256 dos arquivos efetivamente revisados. A revisão usa uma sessão separada do Claude Code, por leitura estática; não equivale à execução de testes ou auditoria humana. Alterações posteriores são descritas aqui e verificadas pelos testes e pela execução final. O modelo retornado foi `claude-fable-5-2`, solicitado pelo alias `fable`, velocidade `standard` nos metadados disponíveis.

## Bloco 00 — arquitetura

- Contradições preliminares foram corrigidas: HistGradientBoosting, limiar fixo 0,30, BH a 5%, bootstrap de 500 e aumento de Brier de 0,05, conforme configuração.
- A previsão de que o PSI de `pay_0` não alcançaria 0,20 foi confrontada com execução: **0,20530782**, sem alterar pesos ou limiar. A margem é pequena e não há IC do PSI: é demonstração de seed fixada, não garantia de detecção em qualquer carteira.
- Hashes ZIP e XLS fixados; artefato inclui limiar/atributos; contrato bloqueia vazio, colunas extras e domínios.
- Diferentes regras do Evidently e política primária são explicitadas no painel e por banner no HTML Evidently. Não se declara concordância universal.
- Conceito/combinado usam intervenção consistente por ID/seed, com pares controle/conceito e covariável/combinado.

## Bloco 01 e rodada 01b — dados/modelo

- Proveniência passou a validar SHA-256 do XLS; erro de integridade foi separado de falha de leitura e protegido por regressão.
- `psi_epsilon` e limiar Brier validados; chaves desconhecidas rejeitadas; URL aprovada tem fonte única; mínimo configurado é consumido.
- Inferência aceita ausência dos três demográficos excluídos. Quando presentes, são validados. Idade permanece: documentação e nome do teste restringem a alegação de exclusão aos atributos realmente excluídos.
- `DataContractError` é lançado fora do tratamento Pandera: sem contexto/causa retendo valores inválidos. Testes exercitam tanto tipos quanto domínio financeiro.
- Cobertura ampliada: cache íntegro/adulterado, configuração positiva/negativa, normalização, volume, métricas conhecidas, classe única, sobreposição, treino separável, carregamento joblib e fonte UCI real quando há cache.
- Referência independente tem métricas finais publicadas. Limiar e hiperparâmetros são escolhas acadêmicas prévias, sem busca em produção; não se alega otimização econômica.
- Defaults explícitos das APIs foram mantidos por conveniência de uso e testes, com argumentos passados pela orquestração validada. Não são parâmetros ocultos do pipeline entregue.

## Bloco 02 e rodada 02b — drift

- Guardas de IDs impedem referência/produção sobrepostas antes de seleção e inferência. Comparação estatística pura ainda permite comparar distribuições iguais, como exigem seus testes.
- Testes passam cenários pelo detector em três seeds controladas e pela base UCI real em cache. O teste real tem skip explícito em clones sem cache; evidências finais vêm da execução integral real.
- `simulation` é persistido explicitamente, sem depender apenas de `DataFrame.attrs` para leitura do resultado.
- Score, taxa de predição positiva e prevalência disponível são monitorados separadamente de X. Rótulo ausente permanece pendente.
- JSON primário é gravado atomicamente antes do Evidently. Falha complementar preserva diagnóstico, grava tipo seguro e interrompe a execução, sem alegar completude.
- O teste pareado **não é um detector causal genérico**: evidencia a intervenção conhecida. O pipeline também alerta degradação não pareada contra referência, como sinal exploratório; não rotula essa comparação como prova de concept drift real.
- Curva dose–resposta, calibração de falso alarme sequencial, reponderação e poder estatístico não foram incluídos: extrapolam a demonstração pedida. Seus limites estão declarados, inclusive severidade0,8, dependência entre cenários e ausência de conclusão macroeconômica.
- Sexo/escolaridade/estado civil não pertencem a FEATURES; a hipótese condicional do parecer sobre KS nesses códigos não se aplica.

## Bloco 03 — observabilidade

- Controle positivo do lote precede violações isoladas, preservando dtype numérico. Ausência de inferência no lote inválido é uma garantia do fluxo validado e inspecionado, não um contador observado de chamadas em sistema remoto.
- Proveniência inclui árvore suja, revisão Git, hashes individuais e agregado do código/configuração/lock. A execução não é atribuída silenciosamente apenas a um HEAD antigo.
- Sanitização remove credenciais, parâmetros e fragmentos de URIs de quaisquer esquemas; caminho SQLite mantém formato necessário à consulta local.
- Disjunção é verificada em dados e novamente na integração. Modelo só ajusta treino; receber validação para medir métricas não significa ajustar nesse conjunto.
- Referência independente, auditoria por grupos e comparação combinada aparecem no HTML; métricas da referência, hiperparâmetros, série por passos e auditoria são registrados no MLflow.
- Links relativos no artefato pai MLflow recebem espelho dos relatórios dos cenários. Arquivo principal e resumo entram no inventário de hashes.
- Etapas de persistência/sincronização são rastreadas; erro e interrupção não viram sucesso. Falhas secundárias de salvamento não substituem a exceção original. CLI informa diretório real e distingue interrupção.
- Supressão complementar de taxas evita dedução trivial de grupos pequenos por dimensão; TPR/FPR exigem denominador específico mínimo. Não se afirma certificação de equidade.
- Disco é medido no diretório de saída; alertas de recursos incluem observado/limiar. Estados insuficientes/indefinidos são exibidos como pendentes.
- Janelas T0–T3 e `step` no MLflow expressam a passagem de tempo **simulada**. São cenários controlados, sem afirmar tendência econômica monotônica ou safras futuras observadas.
- Alertas não pareados são regras exploratórias por efeito, sem IC ou taxa sequencial calibrada; essa limitação é aceita e declarada. O contraste causal da demonstração usa pares e bootstrap.

## Escopo de entrega e limitações

O [README](../../README.md) contém governança e links oficiais. Vídeo não foi produzido; somente roteiro autorizado. Execuções remotas do CI não são alegadas antes de ocorrerem. A validação visual no navegador foi interrompida pela ferramenta por não conseguir confirmar a URL; HTMLs têm testes de conteúdo, links, JSON e integridade, mas não aprovação visual manual.

O hook global corporativo bloqueou a tentativa inicial de commit; foi solicitada autorização para usar hooks locais somente neste repositório acadêmico. Não foi contornado silenciosamente. Estado final do histórico e eventuais pendências constam no registro de progresso.

## Fechamento das rodadas 03b e 04

A rodada 03b aprovou as correções da integração e não encontrou defeito crítico de código. As pendências de evidência foram fechadas pela execução real e pelos registros literais/JUnit vinculados às fontes. Os resíduos de URI malformada, indicação de etapa esperada, rótulo em inglês e HTML isolado em filhos receberam regressões e correções; filhos agora apontam para o pai.

A rodada 04 confirmou todos os números. O defeito real de acentuação em resultados, causado pela passagem por um pipe PowerShell, foi corrigido em disco por gravação UTF-8 direta; o parecer antigo permanece intacto. O README recebeu causalidade, decomposição de Brier, achados por grupo e plano de mitigação sem alegar redução empírica. O roteiro inclui números, folga e uma só execução nas telas. O Evidently realmente aponta 15 colunas com testes brutos; a política primária aponta duas e ambas também passam no Evidently.

Sobre contratos: finitude é uma pré-checagem deliberada; Pandera também contém regras de nulidade, idade, unicidade, limites e domínios. Controle positivo e variantes isoladas comprovam rejeição no fluxo, sem divulgar os `failure_cases`. `rejected_rows` é o volume bloqueado integralmente, não a quantidade de linhas violadoras. Não se afirma coletar todas as causas do lote combinado depois do primeiro bloqueio.

Não foram adicionados IC do PSI, ablação de idade, calibração sequencial ou parecer setorial de crédito real. Esses limites são explicitados; a atividade pede demonstração e plano de governança. A supressão por grupo não se aplica automaticamente a todo histograma Evidently, e metadados locais de execução acompanham o retrato. A revisão autorizada recebeu esses agregados, sem linhas ou IDs de clientes.

Na rodada intermediária, o registro gerado por `scripts/verificar_entrega.py` confirmou **134 testes passando** depois da execução UCI `20261116T212632_471752d41e59`. O fechamento atualizado está abaixo; o bloqueio histórico dos commits foi posteriormente resolvido por autorização expressa do usuário.

A diferença de contagens do Ruff foi investigada no runtime instalado: `ruff format --check --verbose` inclui explicitamente arquivos `.md` (README, AGENTS e documentação); `ruff check --show-files` lista Python/TOML. Portanto, 46 arquivos formatados contra 25 arquivos de lint não representa código Python ausente na identidade. O número do formatador cresce quando um novo parecer Markdown é criado. O contador anterior de 130 testes no pacote 04b foi atualizado em disco para 134 após receber o registro literal, sem alterar o parecer histórico.

## Veredito final e ressalvas aceitas

A rodada **03d** confirmou como corrigidos os três itens da 03c: destino remoto constante, evidência anterior corretamente identificada como derivada e validação por bytes/configuração/manifesto sem depender de `git_dirty`. Seu único importante remanescente era a discriminação das fixtures negativas. A rodada **03e** julgou **CORRIGIDOS** os três casos ID/status/escape, sem defeitos críticos ou importantes nesse escopo. Os pareceres são estáticos; a execução é comprovada separadamente por log e JUnit.

O último congelamento é `20261116T215129_2bee07608434`, com **31 fontes**, hash agregado `312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73` e **150 testes passando**. A CLI original foi capturada em `docs/execucao_cli.json`; o verificador registra sete comandos literais, hashes de artefatos e JUnit. Os metadados MLflow exportam a hierarquia real. O retrato publicado contém apenas a lista agregada inspecionada, sem modelo, banco ou base completa.

Ressalvas menores aceitas: validação de consistência por hashes não é assinatura/autenticidade contra um autor capaz de forjar todos os arquivos; instalações fora do checkout uv/editável não são o modo de uso documentado; logs verbose contêm caminhos de perfis locais; o espião de leitura dos testes acompanha a implementação atual com `Path.read_bytes`; mensagens de ID/status compartilham texto. Há ausência de calibração sequencial e de certificação de equidade, já declaradas. Nenhuma dessas ressalvas é apresentada como garantia implementada.

O hook corporativo também recusou uma tentativa com `feature/observabilidade-credito`. Em seguida, o usuário autorizou expressamente usar hooks locais e esclareceu que os corporativos pertencem aos projetos de trabalho. Foi configurado `core.hooksPath=.git/hooks` apenas neste repositório, preservando a configuração global. Os commits semânticos foram registrados por bloco. Não houve contorno silencioso. Inspeção visual manual e CI remoto têm seus estados próprios; vídeo não foi gravado por instrução de escopo.
