# Confiabilidade de modelos de crédito

Tech Challenge MLET — Fase 4. Pipeline de sustentação de um classificador de inadimplência: **contratos Pandera, cenários controlados de drift, relatórios Evidently, logs estruturados e rastreamento MLflow**.

A [Fase 2](https://github.com/callyafiune/Tech-Challenge-fase-2) orientou a organização em `src/`, parâmetros na raiz, testes e rastreabilidade. Esta fase usa dados financeiros; o recomendador Instacart não foi reaproveitado. Consulte o [enunciado preservado](docs/enunciado.md).

**Vídeo:** somente o [roteiro STAR de cinco minutos](docs/roteiro_star.md) integra esta entrega, conforme solicitado. Gravação e link continuam pendentes para a avaliação; não há vídeo publicado.

**Estado Git:** histórico semântico organizado por ambiente, dados/modelo, drift e observabilidade. Por autorização do usuário, somente este repositório usa `core.hooksPath=.git/hooks`; a configuração global dos projetos de trabalho foi preservada. Branch de entrega: `feature/observabilidade-credito`.

## Executar

Requisitos: Python 3.11 e [uv](https://docs.astral.sh/uv/getting-started/installation/). O primeiro download exige HTTPS para a UCI; depois o cache validado permite repetir sem baixar novamente. O pipeline não exige conta de nuvem, chave de API ou serviço pago.

```powershell
uv sync --frozen
uv run python -m credito_monitorado.cli run --config params.yaml --output artifacts
```

O comando imprime um diretório único com `index.html`, `resumo.json`, `manifesto.json`, `logs.jsonl`, `alertas.json`, `modelo.joblib` e quatro pastas de cenários com HTML/JSON do Evidently. Dados completos, banco MLflow e modelos ficam fora do Git.

```powershell
# Evidências agregadas já incluídas no repositório
uv run python -m http.server 8080 --bind 127.0.0.1 --directory reports/execucao_validada
# Acesse http://127.0.0.1:8080

# Execuções feitas nesta máquina: run pai e quatro filhos
uv run mlflow ui --backend-store-uri sqlite:///artifacts/mlflow.db --host 127.0.0.1 --port 5000
# Acesse http://127.0.0.1:5000
```

Execute os comandos na raiz. A UI MLflow mostra o banco local; para avaliar o repositório sem esse banco, abra o [HTML da execução validada](reports/execucao_validada/index.html). Os componentes gerados pela biblioteca Evidently têm textos próprios em inglês. A documentação, os comentários e o relatório consolidado do projeto estão em português.

## Demonstração e resultados

1. Base financeira pública UCI 350: **30.000 registros**; ZIP e XLS com SHA-256 fixados no código, licença e manifesto.
2. Contrato estrito: dados finitos, colunas conhecidas, ID único, idade **19–100**, limite de crédito positivo e domínios financeiros/categóricos explícitos. Nulo, idade inválida e duplicidade bloqueiam um lote antes da inferência.
3. Split estratificado exclusivo por cliente: treino **15.000**, validação **4.500**, referência independente **4.500**, pool de produção **6.000**. Cada cenário tem 2.500 clientes únicos, podendo compartilhar clientes entre cenários contrafactuais.
4. `HistGradientBoostingClassifier` ajustado apenas no treino; limiar **0,30** definido como política acadêmica antes dos cenários, sem otimização de custo de crédito.
5. Controle, seleção covariável por limite/atraso, mudança condicional sintética do alvo e combinado. O modelo permanece congelado.
6. KS com Benjamini–Hochberg e tamanho de efeito, PSI, Evidently e comparação pareada de Brier com bootstrap.
7. Logs, duração, volume, memória, CPU, disco, alertas e MLflow. Nenhum retreino ou promoção automática.

O baseline alcançou AUROC de validação **0,77357**, contra **0,50000** do classificador ingênuo. Os resultados finais, hashes, intervalos e verificações estão em [resultados](docs/resultados.md) e na [matriz de rastreabilidade](docs/matriz_rastreabilidade.md).

O enunciado associa referência ao treino. Aqui ela é um holdout exclusivo da mesma população histórica, para que desempenho de referência seja medido fora da amostra de ajuste e não induza uma falsa degradação por comparação com métricas de treino.

## Interpretar os alertas

| Sinal | Regra padrão | Interpretação e resposta |
|---|---|---|
| Qualidade | Contrato inválido | Bloquear todo o lote, investigar produtor e corrigir na origem. |
| Data drift | PSI ≥ 0,20 **ou** KS com p BH ≤ 0,05 e D ≥ 0,10 | Investigar composição, ETL e ambiente; não comprova alteração de P(Y\|X). |
| Degradação supervisionada | Queda AUROC ≥ 0,05 ou aumento Brier ≥ 0,05 | Conferir maturação dos rótulos, segmentos e custos; composição também afeta métricas. |
| Conceito simulado pareado | X/probabilidades iguais; aumento Brier ≥ 0,05 e limite inferior IC95% > 0 | Degradação no contrafactual; não identifica causa macroeconômica real. |
| Infraestrutura | Etapa > 120 s, amostra RSS > 2.048 MiB ou disco < 1 GiB | Investigar recursos; limites demonstrativos, sem SLA contratado. |

Os parâmetros efetivos estão em [`params.yaml`](params.yaml). PSI usa suporte compartilhado e suavização; intervalos contínuos são fixados pela referência. KS é corrigido na família das variáveis contínuas; histórico de atraso é discreto e usa PSI. Os testes são exploratórios e não garantem uma taxa operacional de falsos alarmes.

**O resumo próprio governa os alertas.** Evidently usa KS bruto nas contínuas e PSI nas discretas; pode divergir por não aplicar a mesma correção BH e corte de efeito. Cada JSON declara essa diferença. Sem alvo, avaliação supervisionada fica pendente; com classe única, AUROC é indefinida. Isso não significa estabilidade de conceito.

O cenário de conceito é severo: verifica a cadeia de detecção e não estima sensibilidade para mudanças pequenas. O combinado é comparado de forma pareada ao covariável, separando o efeito da intervenção no alvo do efeito da seleção. No par combinado, o contraste é reportado; o alerta específico `CONCEITO_SIMULADO` é emitido apenas para o par conceito/controle. O score também é monitorado no JSON, sem canal adicional de alerta próprio. Consulte [causalidade e limites](docs/causalidade.md).

## Causalidade e leitura do experimento

A seleção covariável consulta apenas limite/atraso, preservando os rótulos. Neste lote, AUROC sobe de 0,7825 no controle para 0,7965 no covariável; drift de entradas não implica necessariamente degradação. No conceito, X e probabilidades ficam iguais, e a inversão sintética condicional de rótulos piora Brier e AUROC. Essa intervenção é deliberadamente severa, sem calibragem econômica.

No combinado, o aumento de Brier contra a referência é aproximadamente **0,249889**: **0,021753** de diferença entre covariável e referência, mais **0,228136** da intervenção pareada. É uma decomposição aritmética da simulação, não uma estimativa causal de inflação, desemprego ou renda. Em produção, investigar primeiro qualidade/ETL, seleção de carteira, política de aprovação e maturação/seleção dos rótulos. Uma causa econômica exigiria variáveis e desenho identificável que esta base não fornece.

## Observabilidade e operação

| Indicador | Unidade/origem | Limitação |
|---|---|---|
| Status | Evento por etapa; falha esperada identificada | Falha inesperada interrompe o fluxo. |
| Duração | Segundos por etapa/execução | Tempo nesta máquina; rede/cache afetam comparação. |
| Volume | Linhas por lote/partição | Contagens não são clientes distintos entre cenários. |
| Drift | Scores, limiares, p ajustado e atributos | Mudança de distribuição não identifica causa. |
| Modelo | AUROC, precisão média, F1, recall, precisão, acurácia, Brier | Depende da cobertura/maturação dos rótulos. |
| Recursos | RSS MiB, CPU acumulada s, disco livre GiB | Amostras nos limites das etapas, sem pico exato ou monitoramento contínuo do host. |
| Alertas | Severidade, motivo e ação recomendada | Persistidos localmente; não enviados a terceiros. |

MLflow registra configuração, hashes, métricas, modelo e relatórios agregados. Não recebe linhas de clientes ou `failure_cases` do Pandera. Falha de tracking invalida a conclusão rastreada. Os relatórios versionados são um retrato da execução identificada, e não monitoramento ao vivo.

Em operação real, engenharia de dados investigaria produtor/ETL; risco de modelo analisaria safras, maturação e custos; infraestrutura trataria recursos. Retreino exige validação independente, equidade, aprovação de risco e rollback. Um PSI alto não basta para substituir o modelo.

## Governança, privacidade e LGPD

**Contexto.** Exercício acadêmico com dados históricos públicos de Taiwan. A base não representa a população brasileira. Licença pública não comprova anonimização nem elimina risco de reidentificação. A LGPD orienta o desenho de uma fintech brasileira hipotética; este projeto não constitui operação de crédito real nem certificação jurídica.

**Finalidade e minimização.** Demonstrar confiabilidade, sem conceder ou negar crédito. Não há nome, CPF, telefone, e-mail ou endereço. O ID só permite separar partições e rastrear localmente; fica fora do modelo, logs e relatórios públicos. Sexo, escolaridade e estado civil não são preditores. A idade permanece como atributo e eixo de auditoria: essa escolha acadêmica pode produzir discriminação e precisa ser reavaliada para uso real. Sexo e idade são auditados de forma agregada. Excluir atributos não remove vieses ou proxies.

**Base legal contextualizada.** Em uma operação brasileira hipotética, o art. 7º, X pode fundamentar o tratamento estritamente necessário à proteção do crédito. Finalidades acessórias exigem avaliação própria. Consentimento não é autorização genérica. Dados sensíveis seguem o regime do art. 11; art. 7º, X não autoriza seu uso indiscriminado. Dados financeiros ligados a pessoa identificável são pessoais, sem serem automaticamente sensíveis na definição legal. Controlador, encarregado e jurídico devem validar finalidade, necessidade, transparência, não discriminação e normas setoriais. [LGPD atualizada, Câmara](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html).

**Inventário e acesso.** Brutos no cache `data/`; modelos, intermediários e banco MLflow em `artifacts/`; ambos ignorados no Git. Relatórios incluem indicadores agregados e metadados/caminhos locais de execução. A supressão mínima por grupo é aplicada à auditoria de equidade; histogramas Evidently podem ter categorias raras. Não se promete anonimização: dados privados exigiriam revisão de divulgação e agregação adicional antes de publicar. A restrição atual é a conta do sistema operacional; não há autenticação de aplicação nem criptografia adicional. Produção exige acesso por função, criptografia, isolamento, cofre de segredos e trilha de acesso. UI e servidor estático devem escutar apenas `127.0.0.1`.

**Retenção.** Política acadêmica proposta: excluir dados brutos, intermediários, modelos, bancos e backups locais até **90 dias após a avaliação**, preservando código e evidências agregadas inspecionadas. Não existe expurgo automático. É um prazo escolhido pelo projeto, não obrigação legal universal. Para a fintech, manter tabela de finalidade, fundamento, prazo e responsável por ativo, com término e exceções dos arts. 15 e 16, bloqueio de finalidade e revisão periódica.

**Direitos e decisões automatizadas.** O protótipo não mantém canal externo de atendimento. Na operação, o controlador deve disponibilizar canal autenticado para os direitos do art. 18, com apoio do encarregado e trilha de atendimento. Art. 20 prevê solicitação de revisão de decisões exclusivamente automatizadas e informação sobre critérios, respeitados segredos comercial/industrial. Revisão por pessoa habilitada é **política recomendada deste projeto**, sem atribuir à lei obrigação geral de revisão humana. [Art. 20, LexML](https://normas.leg.br/?urn=urn%3Alex%3Abr%3Afederal%3Alei%3A2018-08-14%3B13709%21art20).

**Equidade.** Auditoria por sexo e faixas etárias com mínimo de 30 registros, supressão complementar por dimensão e denominadores mínimos para TPR/FPR. Na referência, a diferença de aprovação técnica é **2,18 pontos percentuais por sexo** e **5,90 por idade**. O grupo 50+ apresenta FPR de **15,87%**, contra **11,44%** em 30–49, e AUROC de **0,7477**. São sinais descritivos, sem prova causal ou certificado de justiça. `approval_rate` significa apenas proporção de predições zero, sem concessão real de crédito.

Como mitigação já aplicada, excluem-se ID/sexo/escolaridade/estado civil dos preditores; a política documentada restringe o uso ao exercício acadêmico. Como plano antes de produção: o responsável de risco deve investigar esses gaps, comparar ablação da idade em validação independente, avaliar calibração/custos por segmento e documentar aprovação ou veto. Não se declarou redução empírica do viés: ablação, auditoria interseccional e limiares de aceitação de equidade não foram executados. A base taiwanesa de 2005 exige cautela de generalização.

**Responsabilidades.** Nesta entrega, o executor local responde por reproduzir e inspecionar artefatos. Para produção, designar formalmente controlador, encarregado, engenharia de dados, risco, segurança e atendimento; nenhum integrante ou contato institucional foi inventado. Controlador aprova finalidade/retenção; engenharia mantém contratos; risco aprova suspensão e substituição; segurança coordena incidentes; encarregado orienta direitos e comunicações.

**Incidentes.** Suspender ingestão afetada, restringir acesso, preservar evidências com segurança, avaliar extensão/risco, corrigir causa e registrar decisões. Prever comunicação à ANPD e titulares quando cabível pelo art. 48 e pela Resolução CD/ANPD nº 15/2024. O regulamento prevê, em regra, três dias úteis, com marcos, exceções e eventual regime diferenciado que devem ser conferidos pelo encarregado. Este código não automatiza notificações. [Orientação oficial da ANPD](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis). As revisões expressamente autorizadas enviaram ao Claude Code código, documentação e evidências agregadas, incluindo alertas e metadados/caminhos locais da execução. Não enviaram IDs de clientes ou linhas da base.

## Verificar

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
git diff --check
```

Testes usam fixtures controladas e geração HTML real pelo Evidently, sem download. Casos de cache real têm skip explícito se não há cache local; execução completa com dados reais possui evidência separada. O CI verifica ambiente limpo; seu resultado remoto só existe após rodar no GitHub.

Para registrar stdout literal, JUnit, horários e vínculo ao código de uma execução concluída, use `uv run python -X utf8 scripts/verificar_entrega.py --resumo artifacts/ID_DA_EXECUCAO/resumo.json`. Os arquivos ficam em `docs/validacao/` e o índice em `docs/verificacao.json`. `.env.example` documenta variáveis opcionais; o programa não carrega `.env` automaticamente.

O Git preserva os bytes dos arquivos por `.gitattributes`, evitando que conversões automáticas de fim de linha invalidem os hashes das evidências. Hashes de modelo binário podem mudar por plataforma/versão. Identidade dos dados/configuração, isolamento e métricas com tolerância são verificações relevantes. `joblib` deve carregar somente artefatos confiáveis produzidos nesta execução; arquivo não confiável pode executar código.

No Windows, se o terminal exibir acentos incorretos, use `uv run python -X utf8 -m credito_monitorado.cli run --config params.yaml --output artifacts`. Os relatórios são gravados explicitamente em UTF-8.

## Organização e referências

```text
src/credito_monitorado/   dados, contrato, modelo, drift, observabilidade e orquestração
tests/                   qualidade, isolamento, estatística e operação
scripts/revisar_bloco.py  revisão adversarial independente pelo Claude Code Fable
params.yaml              parâmetros e limiares
docs/                    arquitetura, cards, causalidade, roteiro e revisões
reports/execucao_validada/ HTMLs e evidências agregadas
```

- [Arquitetura](docs/arquitetura.md), [plano](docs/plano_implementacao.md), [progresso](docs/progresso.md) e [tratamento das revisões](docs/revisoes/tratamento.md).
- [Dicionário](docs/dicionario_dados.md), [model card](docs/model_card.md), [causalidade](docs/causalidade.md) e [roteiro](docs/roteiro_star.md).
- Yeh, I. (2009). *Default of Credit Card Clients*. UCI. [DOI 10.24432/C55S3H](https://doi.org/10.24432/C55S3H), [fonte e licença CC BY 4.0](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients).
- [Pandera: DataFrame Schemas](https://pandera.readthedocs.io/en/stable/dataframe_schemas.html), [Evidently: API atual](https://docs.evidentlyai.com/quickstart_ml).
