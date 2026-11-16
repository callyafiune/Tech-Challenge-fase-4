# Guia de execução e operação

[Voltar ao README](../README.md).

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

Execute os comandos na raiz. A UI MLflow mostra o banco local; para avaliar o repositório sem esse banco, abra o [HTML da execução validada](../reports/execucao_validada/index.html). Os componentes gerados pela biblioteca Evidently têm textos próprios em inglês. A documentação, os comentários e o relatório consolidado do projeto estão em português.

## Interpretar os alertas

| Sinal | Regra padrão | Interpretação e resposta |
|---|---|---|
| Qualidade | Contrato inválido | Bloquear todo o lote, investigar produtor e corrigir na origem. |
| Data drift | PSI ≥ 0,20 **ou** KS com p BH ≤ 0,05 e D ≥ 0,10 | Investigar composição, ETL e ambiente; não comprova alteração de P(Y\|X). |
| Degradação supervisionada | Queda AUROC ≥ 0,05 ou aumento Brier ≥ 0,05 | Conferir maturação dos rótulos, segmentos e custos; composição também afeta métricas. |
| Conceito simulado pareado | X/probabilidades iguais; aumento Brier ≥ 0,05 e limite inferior IC95% > 0 | Degradação no contrafactual; não identifica causa macroeconômica real. |
| Infraestrutura | Etapa > 120 s, amostra RSS > 2.048 MiB ou disco < 1 GiB | Investigar recursos; limites demonstrativos, sem SLA contratado. |

Os parâmetros efetivos estão em [`params.yaml`](../params.yaml). PSI usa suporte compartilhado e suavização; intervalos contínuos são fixados pela referência. KS é corrigido na família das variáveis contínuas; histórico de atraso é discreto e usa PSI. Os testes são exploratórios e não garantem uma taxa operacional de falsos alarmes.

**O resumo próprio governa os alertas.** Evidently usa KS bruto nas contínuas e PSI nas discretas; pode divergir por não aplicar a mesma correção BH e corte de efeito. Cada JSON declara essa diferença. Sem alvo, avaliação supervisionada fica pendente; com classe única, AUROC é indefinida. Isso não significa estabilidade de conceito.

O cenário de conceito é severo: verifica a cadeia de detecção e não estima sensibilidade para mudanças pequenas. O combinado é comparado de forma pareada ao covariável, separando o efeito da intervenção no alvo do efeito da seleção. No par combinado, o contraste é reportado; o alerta específico `CONCEITO_SIMULADO` é emitido apenas para o par conceito/controle. O score também é monitorado no JSON, sem canal adicional de alerta próprio. Consulte [causalidade e limites](causalidade.md).

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
