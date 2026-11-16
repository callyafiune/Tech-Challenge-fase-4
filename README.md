# Confiabilidade de Modelos de Crédito — Tech Challenge Fase 4

![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![uv](https://img.shields.io/badge/uv-ambiente%20reprodut%C3%ADvel-DE5FE9)
![scikit-learn](https://img.shields.io/badge/scikit--learn-modelo%20de%20cr%C3%A9dito-F7931E)
![pandas](https://img.shields.io/badge/pandas-dados-150458)
![Pandera](https://img.shields.io/badge/Pandera-contratos-5B5EA6)
![Evidently](https://img.shields.io/badge/Evidently-relat%C3%B3rios%20de%20drift-ED0400)
![SciPy](https://img.shields.io/badge/SciPy-estat%C3%ADstica-8CAAE6)
![MLflow](https://img.shields.io/badge/MLflow-rastreamento-0194E2)
![Pytest](https://img.shields.io/badge/Pytest-testes-0A9EDC)
![Ruff](https://img.shields.io/badge/Ruff-lint%20%2B%20format-D7FF64)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI-2088FF)

Pipeline de sustentação de um classificador de inadimplência: valida dados antes da inferência, simula e detecta drift, acompanha desempenho e registra a saúde da execução. **Pandera + scikit-learn + Evidently + MLflow**, com relatórios HTML e plano de governança.

A organização segue a [Fase 2](https://github.com/callyafiune/Tech-Challenge-fase-2), agora com dados financeiros. Consulte o [enunciado](docs/enunciado.md). **Vídeo: somente o [roteiro STAR](docs/roteiro_star.md); a gravação não foi realizada, conforme solicitado.**

## Pré-requisitos e execução

| Requisito | Observação |
|---|---|
| Python | 3.11 recomendado; projeto aceita 3.11 e 3.12. |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Instala as dependências fixadas em `uv.lock`. |
| Acesso HTTPS à UCI | Necessário no primeiro download; depois é usado o cache validado. |
| Serviços externos | Não exige conta de nuvem, chave de API ou serviço pago. |

Na raiz do repositório:

```powershell
uv sync --frozen
uv run python -m credito_monitorado.cli run --config params.yaml --output artifacts
```

O comando informa o diretório da execução com painel, métricas, logs, alertas, modelo e relatórios dos quatro cenários. Parâmetros em [`params.yaml`](params.yaml); cache, UTF-8 e detalhes no [guia de operação](docs/operacao.md).

## Relatórios e rastreamento

| Entregável | Como consultar |
|---|---|
| Painel da execução validada | [HTML consolidado](reports/execucao_validada/index.html); para navegação local, usar o servidor abaixo. |
| Métricas e evidências | [Resultados](docs/resultados.md), [resumo JSON](reports/execucao_validada/resumo.json) e [manifesto](reports/execucao_validada/manifesto.json). |
| MLflow | Banco local criado pelo pipeline; um run pai e quatro filhos. [Metadados exportados](docs/evidencias_mlflow.json) disponíveis sem o banco. |

```powershell
# Painel incluído no repositório: http://127.0.0.1:8080
uv run python -m http.server 8080 --bind 127.0.0.1 --directory reports/execucao_validada
```

```powershell
# Após executar o pipeline: http://127.0.0.1:5000
uv run mlflow ui --backend-store-uri sqlite:///artifacts/mlflow.db --host 127.0.0.1 --port 5000
```

São retratos de execuções, sem monitoramento ao vivo. Dados completos, modelos e banco MLflow ficam fora do Git. Componentes da biblioteca Evidently mantêm seus textos em inglês.

## Dados, modelo e contratos

| Item | Implementação |
|---|---|
| Base | UCI *Default of Credit Card Clients*: 30.000 registros de Taiwan, licença CC BY 4.0 e hashes de integridade. |
| Partições | Treino: 15.000; validação: 4.500; referência: 4.500; pool de produção: 6.000. Clientes exclusivos entre partições. |
| Modelo | `HistGradientBoostingClassifier`; limiar fixo de 0,30. Ajustado apenas no treino e congelado nos cenários. |
| Contratos | Sem nulos ou valores não finitos; ID único; idade de 19 a 100 anos; limite de crédito positivo; domínios financeiros e categóricos válidos. |
| Bloqueio demonstrado | Nulos, idade inválida e duplicidade causam rejeição antes da inferência. |
| Cenários | Controle, covariável, conceito simulado e combinado; 2.500 clientes por cenário, com sobreposição permitida entre pares contrafactuais. |

A referência é uma amostra independente da mesma população histórica, separada do ajuste para evitar comparação com desempenho de treino. Consulte o [dicionário de dados](docs/dicionario_dados.md) e o [model card](docs/model_card.md).

## Resultados

Na validação, o modelo alcançou **AUROC 0,7736**, contra **0,5000** do classificador ingênuo. A referência independente teve AUROC **0,7674** e Brier **0,1380**.

| Cenário | AUROC ↑ | Brier ↓ | Entradas com drift pela política do projeto |
|---|---:|---:|---|
| Controle | 0,7825 | 0,1303 | Nenhuma |
| Covariável | 0,7965 | 0,1597 | `limit_bal`, `pay_0` |
| Conceito simulado | 0,4073 | 0,4775 | Nenhuma |
| Combinado | 0,4649 | 0,3879 | `limit_bal`, `pay_0` |

Maior AUROC e menor Brier são melhores. No covariável, `limit_bal` apresentou KS D = **0,1815** e `pay_0`, PSI = **0,2053**. A execução validada durou **38,67 s**, com **22 eventos e oito alertas**; esse tempo não é benchmark de produção.

Valores completos, intervalos, divergências entre políticas de detecção e hashes estão em [resultados](docs/resultados.md). Recursos são amostrados por etapa, sem garantia de captura do pico.

## Alertas e causalidade

| Sinal | Critério | Resposta |
|---|---|---|
| Qualidade | Contrato inválido | Bloquear lote e corrigir na origem. |
| Data drift | PSI ≥ 0,20 ou KS com p ajustado BH ≤ 0,05 e D ≥ 0,10 | Investigar composição e ETL. |
| Desempenho | Queda de AUROC ≥ 0,05 ou aumento de Brier ≥ 0,05 | Conferir rótulos, segmentos e custos. |
| Conceito simulado | Entradas/probabilidades iguais; aumento pareado de Brier ≥ 0,05 e limite inferior do IC95% > 0 | Investigar a mudança controlada do alvo. |
| Infraestrutura | Etapa > 120 s, RSS > 2.048 MiB ou disco livre < 1 GiB | Investigar recursos; limites demonstrativos. |

**Drift de entradas não comprova mudança em P(Y\|X) nem degradação:** a AUROC sobe no cenário covariável. Na intervenção sintética de conceito, entradas e probabilidades são preservadas, mas os rótulos mudam; o Brier aumenta **0,3472** contra o controle.

A simulação é severa e não identifica efeitos reais de inflação, desemprego ou renda. Sem rótulos maduros, a avaliação supervisionada fica pendente. O resumo próprio governa os alertas; a política bruta do Evidently pode divergir. Detalhes em [causalidade](docs/causalidade.md) e [operação](docs/operacao.md).

## Governança, privacidade e LGPD

Plano para uma fintech brasileira hipotética; o exercício usa dados públicos históricos de Taiwan e não realiza decisões reais de crédito. Licença pública não comprova anonimização ou conformidade com a LGPD.

| Tema | Política e limites |
|---|---|
| Finalidade e minimização | Demonstrar confiabilidade. ID, sexo, escolaridade e estado civil fora dos preditores; idade permanece e exige reavaliação. Logs não recebem linhas ou IDs de clientes. |
| Base legal | Art. 7º, X, é hipótese contextual para proteção do crédito, sujeita à validação jurídica. Dados sensíveis seguem o art. 11. |
| Armazenamento e acesso | `data/` e `artifacts/` ignorados no Git; relatórios públicos agregados. Acesso atual pela conta do sistema; produção exige controle por função, criptografia e revisão de divulgação. Serviços locais em `127.0.0.1`. |
| Retenção | Proposta de exclusão de dados, modelos, bancos e backups até 90 dias após a avaliação; sem expurgo automático. Preservar código e evidências agregadas inspecionadas. |
| Direitos | Produção exige canal para os direitos do art. 18 e revisão de decisões automatizadas do art. 20. Revisão humana é política recomendada do projeto. |
| Equidade | Auditoria agregada com supressão de grupos pequenos. Diferenças de aprovação técnica: 2,18 pontos percentuais por sexo e 5,90 por idade; sem comprovação de redução de viés. |
| Responsáveis | Executor local nesta entrega; em produção, designar controlador, encarregado, dados, risco, segurança e atendimento. Substituição do modelo exige validação, aprovação e rollback. |
| Incidentes | Suspender ingestão afetada, restringir acesso, preservar evidências e avaliar comunicação à ANPD/titulares. Sem notificações ou retreino automáticos. |

O [plano completo de governança](docs/governanca.md) reúne fundamentos legais, retenção, responsabilidades, incidentes, riscos de reidentificação e medidas de equidade. A [análise causal](docs/causalidade.md) detalha os limites das conclusões.

## Qualidade

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
git diff --check
```

A [verificação registrada](docs/verificacao.json) contém **150 testes aprovados** e 11 avisos de depreciação de dependências. [CI no GitHub Actions](https://github.com/callyafiune/Tech-Challenge-fase-4/actions/workflows/ci.yml). Procedimentos de reprodução e auditoria no [guia de operação](docs/operacao.md).

## Documentação

| Assunto | Referência |
|---|---|
| Arquitetura e módulos | [Arquitetura](docs/arquitetura.md) |
| Planejamento e acompanhamento | [Plano](docs/plano_implementacao.md) e [progresso](docs/progresso.md) |
| Fonte, campos e licença | [Dicionário de dados](docs/dicionario_dados.md) e [UCI — DOI 10.24432/C55S3H](https://doi.org/10.24432/C55S3H) |
| Modelo e limitações | [Model card](docs/model_card.md) |
| Estatística e evidências | [Resultados](docs/resultados.md) e [matriz de rastreabilidade](docs/matriz_rastreabilidade.md) |
| Execução e alertas | [Guia de operação](docs/operacao.md) |
| Privacidade e hipóteses causais | [Governança](docs/governanca.md) e [causalidade](docs/causalidade.md) |
| Revisões com Claude Code Fable | [Tratamento dos pareceres](docs/revisoes/tratamento.md) |
| Conferência dos requisitos | [Auditoria final](docs/auditoria_final.md) |
| Apresentação em até cinco minutos | [Roteiro STAR](docs/roteiro_star.md) |
