# Dicionário e proveniência

Fonte: Yeh, I. (2009), *Default of Credit Card Clients*, [UCI 350](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients), [DOI 10.24432/C55S3H](https://doi.org/10.24432/C55S3H), CC BY 4.0. Dados de Taiwan, histórico financeiro de abril a setembro de 2005 e alvo de inadimplência do mês seguinte. Não são dados brasileiros nem uma série de safras futuras.

O download oficial é um ZIP com XLS. O cabeçalho é lido com `header=1`; nomes são convertidos para minúsculas, `ID` vira `record_id` e `default payment next month` vira `target`. Nenhum valor financeiro é imputado ou recodificado. A normalização não remove linhas.

| Arquivo | SHA-256 aprovado |
|---|---|
| ZIP UCI | `56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602` |
| XLS extraído | `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933` |

O manifesto local registra origem, licença, aquisição, hashes e natureza real. Mudança nos bytes exige revisão explícita; não há substituição por base sintética para produzir a entrega. Dados sintéticos são usados somente nos testes unitários/integração.

| Coluna normalizada | Significado / unidade | Contrato e uso |
|---|---|---|
| `record_id` | Identificador sequencial da fonte | Inteiro positivo, único por lote; não preditor; não publicado. |
| `limit_bal` | Limite de crédito em dólares taiwaneses NT$ | > 0 e ≤ 2.000.000; preditor. **Não é renda**. |
| `age` | Idade em anos | Inteira 19–100; preditor e auditoria. |
| `sex` | Código UCI: 1 masculino, 2 feminino | Não preditor; auditoria agregada; fonte não cobre outras identidades. |
| `education` | 1 pós-graduação, 2 universidade, 3 ensino médio, 4 outros | Inteiros 0–6; códigos 0, 5, 6 observados são preservados, sem significado inventado; não preditor. |
| `marriage` | 1 casado, 2 solteiro, 3 outros | Inteiros 0–3; código 0 não descrito é preservado; não preditor. |
| `pay_0`, `pay_2`…`pay_6` | Situação do pagamento de setembro, agosto…abril | Inteiros -2 a 8 observados na fonte; -1 indica pagamento em dia e valores positivos representam meses de atraso conforme catálogo. Os demais códigos são preservados sem interpretação adicional. Preditores. |
| `bill_amt1`…`bill_amt6` | Fatura em NT$, setembro…abril | -1.000.000 a 2.000.000, finita; saldo negativo pode ser legítimo; preditores. |
| `pay_amt1`…`pay_amt6` | Pagamento anterior em NT$, setembro…abril | 0 a 2.000.000, finito; preditores. |
| `target` | Inadimplência no mês seguinte | Inteiro binário: 1 inadimplência, 0 não inadimplência. Nunca preditor. |
| `probability` | Probabilidade estimada de inadimplência | Saída [0,1], sem garantia de calibração para outra população. |
| `prediction` | Decisão técnica de risco | 1 se probabilidade ≥ 0,30. Não é uma decisão real de concessão de crédito. |

O domínio do contrato é uma política desta demonstração para a versão fixada, não um resumo universal dos códigos/limites financeiros. Não aceitar textos numéricos ou truncar fracionários para contornar regras. Colunas desconhecidas, nulos, infinitos, lote vazio e duplicatas de ID bloqueiam a ingestão. Na inferência, o alvo e os três demográficos excluídos são opcionais; quando presentes, são validados. No treino/auditoria, a base completa é validada.

Partições estratificadas: `train` 50%, `validation` 15%, `reference` 15%, `production_pool` 20%, com seed 42. O manifesto contém hashes e contagens, sem os próprios IDs. Clientes não cruzam partições. Perfis financeiros idênticos podem corresponder a IDs diferentes na fonte; exclusão por ID não comprova independência total dos perfis, uma limitação da base pública.
