# Roteiro STAR — até cinco minutos

**Estado:** roteiro pronto; vídeo não gravado por solicitação do usuário. Não há link de vídeo.

O retrato entregue usa a execução `20261116T220412_87839641f75d`. Nesta máquina ela pode ser consultada no MLflow pelo run pai indicado em `docs/resultados.md`; em outro clone, use o novo ID gerado localmente.

Preparar antes da gravação: executar o pipeline; abrir o HTML consolidado e o Evidently covariável da **mesma execução**; abrir seu run pai no MLflow; deixar README, `params.yaml` e saída do pytest disponíveis. O ID deve coincidir nas telas. Em outro clone, o run da entrega não existe: usar o novo ID local e servir `artifacts/ID_DA_EXECUCAO`, sem misturar com o retrato versionado. Usar somente telas agregadas.

| Tempo | STAR | Fala sugerida e demonstração |
|---|---|---|
| 0:00–0:40 | Situação | “Uma fintech pode continuar respondendo normalmente enquanto seu modelo de crédito perde qualidade. Dados fora do contrato e mudanças no perfil dos clientes podem causar decisões ruins sem falha de infraestrutura.” Mostrar título/objetivo do README. |
| 0:40–1:10 | Tarefa | “Construí uma camada de confiabilidade: impedir ingestão inválida, detectar mudança de distribuição, acompanhar desempenho com rótulos e manter rastreabilidade e governança.” Mostrar arquitetura e as quatro etapas. |
| 1:10–1:50 | Ação: qualidade e baseline | “Usei 30 mil registros públicos de crédito da UCI, separados por cliente em treino, validação, referência e produção. Pandera rejeita nulo, idade inválida e duplicata antes de qualquer inferência.” Mostrar bloco de contrato rejeitado no relatório e as contagens. “O baseline supera o classificador ingênuo na validação.” |
| 1:50–2:40 | Ação: drift | “O cenário covariável muda a seleção por limite e atraso sem consultar o alvo. O painel primário aponta duas variáveis: limite com KS D de 0,182 e atraso com PSI de 0,205. O Evidently bruto marca 15 de 20 colunas; aplicamos BH e efeito mínimo para a decisão primária.” Abrir Evidently e resumo. “A margem do PSI é pequena: esse corte é demonstrativo, não certeza operacional.” |
| 2:40–3:20 | Ação: conceito | “Neste contrafactual, entradas e probabilidades ficam idênticas ao controle; alterei apenas os rótulos segundo regra conhecida. O aumento pareado do Brier e seu intervalo mostram a degradação.” Mostrar comparação pareada. “É uma simulação severa, não evidência de que inflação causou o problema.” |
| 3:20–3:55 | Ação: operação e governança | Mostrar estágios, duração, volume e recursos; depois o run pai e filhos da mesma execução. “Tracking registra configuração, hashes e métricas. O contrato interrompe dados ruins. Excluímos atributos, auditamos grupos e documentamos retenção e direitos; isso é um plano acadêmico, sem certificação de conformidade.” |
| 3:55–4:30 | Resultado | Mostrar tabela final e testes. “O contrato bloqueou o lote, houve oito alertas e drift nas duas entradas. No conceito simulado, AUROC caiu de 0,783 para 0,407 e Brier aumentou 0,347, com IC95% de 0,327 a 0,368. Sem rótulos, conceito fica pendente. O covariável sozinho não piorou a AUROC.” Conferir números caso a execução local tenha parâmetros diferentes. |
| 4:30–4:50 | Resultado e limites | “Não há crédito real nem retreino automático. O alerta exige investigação e aprovação de risco. A lição é combinar qualidade, modelo e operação, sem confundir mudança de distribuição com uma causa econômica.” Encerrar no README. Reservar dez segundos de folga. |

Comandos para preparar as telas:

```powershell
uv sync --frozen
uv run python -m credito_monitorado.cli run --config params.yaml --output artifacts
uv run python -m http.server 8080 --bind 127.0.0.1 --directory artifacts/ID_DA_EXECUCAO
uv run mlflow ui --backend-store-uri sqlite:///artifacts/mlflow.db --host 127.0.0.1 --port 5000
uv run pytest -q
```

Substituir `ID_DA_EXECUCAO` pelo diretório impresso no terminal. Abrir servidor estático e MLflow em terminais separados. Não executar o pipeline inteiro durante a fala; mostrar uma execução previamente concluída. Se optar pelo retrato versionado, usar somente telas daquele ID e seu banco original nesta máquina. Ensaiar para até 4:50 e reduzir trocas de tela se necessário.
