# Model card — baseline de inadimplência

## Finalidade e população

Demonstrar sustentação e observabilidade de um classificador binário. Alvo positivo: inadimplência no mês seguinte. Base UCI 350 com 30.000 clientes históricos de Taiwan. Não usar para concessão real no Brasil: não houve validação local, regulatória ou econômica.

## Modelo e desenvolvimento

`HistGradientBoostingClassifier`, scikit-learn, com `max_iter=150`, `learning_rate=0.08`, `max_leaf_nodes=15`, seed 42 e sem early stopping. O `ColumnTransformer` restringe as entradas a 20 variáveis financeiras/idade; ID, alvo, sexo, escolaridade e estado civil são excluídos. Os parâmetros são escolhas de baseline acadêmico, sem busca otimizada em referência ou produção.

Somente 15.000 registros de treino participam do ajuste. Validação com 4.500 permite comparar com `DummyClassifier(strategy='prior')`; referência holdout independente com 4.500 recebe avaliação final e serve de referência de monitoramento. Pool exclusivo com 6.000 alimenta os cenários. Limiar 0,30 é fixado na configuração, sem seleção em produção. Esse limiar não corresponde a uma política econômica validada.

O bundle persistido inclui modelo, limiar e lista de atributos; a reprodução verifica igualdade de probabilidades após recarregar o artefato confiável. A identidade é documentada por hashes de configuração, fonte e artefato. Dependências estão no `uv.lock`.

## Avaliação e limitações

Validação inicial: AUROC **0,77357**, F1 **0,5152**, Brier **0,13812**. Dummy AUROC **0,50**. Os números finais de referência e cenários constam no [relatório de resultados](resultados.md); a leitura deve considerar a prevalência e o limiar. AUC mede ordenação; Brier mede erro das probabilidades; F1 depende de limiar e composição. Não há avaliação de lucro, perda esperada, calibração prospectiva ou política de precificação.

Os rótulos de controle/covariável são originais. Nos cenários de conceito/combinado, são contrafactuais sintéticos para provar funcionamento do detector. Não interpretar esse desempenho como estimativa de uma recessão real. A severidade é uma verificação de sanidade, não uma curva de sensibilidade.

Idade é utilizada e pode induzir discriminação. Excluir sexo/escolaridade/estado civil não remove proxies. A auditoria agregada por sexo/faixa etária, com supressão de grupos pequenos, identifica diferenças que exigem investigação; não estabelece justiça. A fonte histórica tem limitações de representatividade e categorias demográficas restritas.

## Operação e mudanças

Contrato precede inferência. Alerta de drift demanda investigação de dados/rotulagem/segmentos; ausência de alvo impede afirmar estabilidade de conceito. Nenhum retreino ou registro em estágio de produção ocorre automaticamente. Mudanças exigem comparação independente, custos, equidade, aprovação de risco e rollback. Atualizar versão/configuração e repetir evidências antes da substituição.

O protótipo roda localmente, com amostras de recursos nos limites das etapas e MLflow. A UI local não implementa autenticação de produção. Não carregar arquivos joblib de fonte desconhecida.
