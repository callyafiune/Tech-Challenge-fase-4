# Resultados da execução validada

Execução **`20261116T220412_87839641f75d`**, iniciada em **16/11/2026 às 19:04:12 (America/Sao_Paulo)**, equivalente a `2026-11-16T22:04:12.920707+00:00`. Estado: **sucesso**.

Duração medida: **38,67 s**; **22 eventos e oito alertas**. Inclui a sincronização medida e exclui a cópia final de fechamento dos retratos; não é benchmark de produção.

[Painel HTML](../reports/execucao_validada/index.html), [resumo completo](../reports/execucao_validada/resumo.json), [manifesto](../reports/execucao_validada/manifesto.json) e [inventário dos arquivos publicados](../reports/execucao_validada/publicacao.json).

## Dados e modelo

Fonte UCI real: **30.000 registros**. Treino 15.000, validação 4.500, referência 4.500 e pool 6.000, exclusivos por ID. Quatro lotes de 2.500, com sobreposição contrafactual permitida somente entre cenários.

| Avaliação | AUROC | Brier | F1 |
|---|---:|---:|---:|
| Validação | 0,773570 | 0,138121 | 0,515200 |
| Referência independente | 0,767351 | 0,137971 | 0,529291 |

Dummy AUROC na validação: **0,50**. Limiar fixo 0,30; o carregamento do bundle preservou as probabilidades. Somente treino ajustou o estimador.

## Cenários e estatísticas

| Janela simulada | Cenário | AUROC | Brier | Entradas com drift |
|---|---|---:|---:|---|
| T0 | Controle | 0,782513 | 0,130344 | nenhuma |
| T1 | Covariável | 0,796500 | 0,159724 | limit_bal, pay_0 |
| T2 | Conceito simulado | 0,407339 | 0,477542 | nenhuma |
| T3 | Combinado | 0,464895 | 0,387860 | limit_bal, pay_0 |

No covariável, `limit_bal` tem **KS D = 0,181511**, p ajustado BH = **1,393 × 10⁻⁴⁵**; `pay_0` tem **PSI = 0,205308**, acima do limiar 0,20. Pesos 3 e 4, seed 42 e limiares estão registrados na configuração e reproduzem esta demonstração; não representam calibração operacional.

A margem do PSI é apenas 0,0053 e não há intervalo bootstrap desse índice. A flag demonstra a política na seed fixada; não garante estabilidade da decisão em novas amostras. O Evidently bruto marca **15 de 20 colunas** no covariável e combinado, contra **duas** na política BH/efeito. Seu PSI de `pay_0` é **0,202018**, e o KS bruto de `limit_bal` tem p de **9,951 × 10⁻⁴⁷**. Ambos também cruzam seus limiares no Evidently. Controle e conceito têm zero colunas com drift bruto. As listas diferem porque as políticas de detecção usam critérios distintos.

| Par contrafactual | Aumento Brier | IC95% pareado | X e probabilidades idênticos |
|---|---:|---|---|
| Conceito menos controle | 0,347198 | [0,327206; 0,367646] | sim |
| Combinado menos covariável | 0,228136 | [0,211196; 0,244529] | sim |

Bootstrap pareado de 500 reamostragens. Rótulos de conceito/combinado são sintéticos. A sequência T0–T3 é simulada, sem comprovar tendência econômica ou desempenho futuro. Alertas não pareados são exploratórios. A intervenção severa verifica a cadeia de sanidade, sem calibrar poder contra drift pequeno.

## Operação e rastreabilidade

Contrato: controle positivo aceito; nulo, idade e duplicidade rejeitados isoladamente e no lote combinado. O bloqueio é esperado; nenhuma inferência é executada nesse ramo do fluxo. Não houve falha inesperada.

MLflow pai: **`b987bfd1e9a848179a2bdeec3eb526fc`**; banco local em `artifacts/mlflow.db`. [Metadados exportados do pai e dos quatro filhos](evidencias_mlflow.json) incluem `mlflow.parentRunId`, experimento, horários, nomes e artefatos, além de IDs, estados e métricas agregadas. O banco não integra o Git; os filhos apontam para os relatórios completos do pai.

O [resumo](../reports/execucao_validada/resumo.json) contém amostras RSS, CPU e disco por etapa. Recursos são amostrados nos limites das etapas e não representam picos exatos ou monitoramento contínuo do host.

Hash canônico da configuração: `25e79a5462f77c394b2162d8989651682614cd2172cd66d5f68181d750441790`.

Hash agregado de fontes/configuração/lock: `312c6ae2f7e8cecf07e52930e28172bf34a44de4021c80e7cf10bf72061d3c73`. O manifesto traz os hashes individuais de 31 arquivos. A execução partiu da **árvore limpa**, no commit **`11dd2b83b57a77ceda8186d6c61b79e20e0dca35`**, que já contém o código e o histórico por blocos.

## Verificação e limites

[Registro dos comandos com caminhos sanitizados](verificacao.json): Ruff aprovado e **150 testes passaram**, com **11 avisos de depreciação** das dependências, sem skips na máquina com cache UCI. O [log com caminhos sanitizados](validacao/03-comando.log) e o [JUnit](validacao/pytest.xml) acompanham horários e hash das fontes. Incluem Evidently real, sucesso SQLite, links dos artefatos e rejeição de evidências adulteradas. O verificador identifica o estado do pipeline como derivado de seu resumo; a [captura independente da CLI original](execucao_cli.json) e seu [stdout com caminhos sanitizados](validacao/00-pipeline-cli.log) registram comando, horários e código de saída zero observado. Esta evidência é local; o [CI remoto](https://github.com/callyafiune/Tech-Challenge-fase-4/actions/workflows/ci.yml) tem seu estado próprio.

Os HTMLs foram verificados automaticamente quanto a conteúdo, links e integridade. O retrato contém apenas relatórios e indicadores agregados; modelo, base completa, predições individuais e banco foram excluídos. O resumo de governança no README e o plano em [governança](governanca.md) são contextualizados para o exercício acadêmico, sem certificação de conformidade.
