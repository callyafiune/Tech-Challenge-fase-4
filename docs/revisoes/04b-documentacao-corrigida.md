# Revisão adversarial — 04b-documentacao-corrigida

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão adversarial — correções 04

Revisei apenas o texto do pacote, sem executar nada. Não tive acesso a código, `resumo.json`, `alertas.json`, `monitoring.json` nem `docs/validacao/*`, então o que depende deles segue não comprovado, incluindo os números de equidade do README.

## Críticos

Nenhum defeito crítico encontrado. Não há indício de vazamento treino/teste, invalidade estatística ou exposição de dado individual no material entregue.

## Importantes

1. **Contagem de testes divergente** — `docs/resultados.md`, seção "Verificação e limites".
   - **Defeito:** o texto diz "130 testes passaram", mas o stdout literal em `docs/verificacao.json` diz `134 passed, 11 warnings` (72 + 62 pontos = 134).
   - **Impacto:** quebra a alegação central desta rodada de "mesmos números".
   - **Correção:** trocar para 134 e procurar "130" em `auditoria_final.md`, `progresso.md` e `tratamento.md`.

2. **Contagens do Ruff incompatíveis** — `docs/verificacao.json`, comandos 2 e 6.
   - **Defeito:** `ruff format --check .` relata 46 arquivos, enquanto `ruff check . --show-files` lista 25 (24 `.py` mais `pyproject.toml`), com 50 s de intervalo. Com descoberta padrão eu esperaria 24 nos dois; a configuração do Ruff não está no pacote, então não sei a causa.
   - **Impacto:** a evidência "literal" fica internamente inconsistente.
   - **Correção:** explicar a diferença no registro ou alinhar os dois escopos.

3. **Evidências aparentemente fora do índice Git** — `docs/evidencias_mlflow.json`, `docs/validacao/`, `scripts/verificar_entrega.py`.
   - **Defeito:** no status da versão analisada (pode estar defasado), nenhum dos três aparece entre os arquivos staged. Vários outros estão `AM`/`MM`, ou seja, o índice guarda versões antigas.
   - **Impacto:** quando o commit for liberado, o link de `resultados.md` para os metadados MLflow quebra. Se `verificar_entrega.py` for uma das 30 fontes, o hash agregado não é reproduzível em clone limpo. `git diff --check` também não cobre arquivos não rastreados.
   - **Correção:** refazer o staging completo e rodar a verificação de novo antes do commit.

4. **Elos frágeis na cadeia de verificação** — `docs/verificacao.json`.
   - **Execução não observada:** `execucao_real.comando` e `codigo_saida: 0` descrevem um processo de 21:26:32, anterior à janela do verificador (21:28:03). São valores derivados de `resumo.json`; rotule-os como declarados.
   - **Origem do hash:** o arquivo não diz se `source_sha256` foi recalculado na hora dos testes ou copiado do manifesto. Sem isso, não prova que os testes rodaram sobre as mesmas 30 fontes; registre os dois valores e a comparação.
   - **Arquivos sem hash:** `pytest.xml` e `evidencias_mlflow.json` não têm SHA-256 no índice.

5. **Hierarquia pai/filhos não demonstrada** — `docs/evidencias_mlflow.json`.
   - **Defeito:** os filhos trazem só `relatorio_run_pai`, que o próprio `resultados.md` descreve como ponteiro para relatórios. Faltam `mlflow.parentRunId`, experimento, horários de início/fim e a tag que liga cada run ao `execution_id`.
   - **Impacto:** "comprovam IDs, estados e métricas" é mais forte do que o arquivo sustenta.
   - **Correção:** exportar esses campos ou suavizar o texto.

## Menores

- **Espaços faltando em `docs/matriz_rastreabilidade.md`:** "real30.000", "validação0,77357", "Dummy0,50", "deltaBrier", "pai+4filhos", "até5min".
- **Matriz incompleta:** R05 aponta o Evidently como evidência de drift em duas colunas sem dizer que ele marca 15 de 20. R07 não liga para `evidencias_mlflow.json`.
- **Tela e fala no roteiro (1:50–2:40):** a fala cita PSI 0,205 com o Evidently aberto, que mostra 0,202. Indique o painel primário para 0,182/0,205 e o Evidently só para "15 de 20".
- **ID ausente no roteiro:** ele exige "mesma execução", mas não cita `20261116T212632_471752d41e59`.
- **Omissão no roteiro:** "o covariável sozinho não piorou a AUROC" é verdadeiro, mas o Brier subiu de 0,130 para 0,160, abaixo do limiar. Vale uma frase.
- **Fragilidade do PSI:** `resultados.md` cita só a margem 0,0053. No PSI do Evidently ela é 0,0020, e "seus limiares" não informa o valor configurado.
- **Alegação sem prova:** "pesos e limiares não foram alterados para forçar esse resultado" não é verificável com um único commit. Marque como declaração.
- **Redação no README:** "impede-se uso real do protótipo" descreve uma restrição documental, não um controle técnico.
- **Alertas:** a composição dos oito não está discriminada em `resultados.md`.
- **`.gitattributes`:** `reports/**` desliga só `blank-at-eol`; `blank-at-eof` e `space-before-tab` continuam ativos, ao contrário do comentário. Use `-whitespace`.
- **Árvore do README:** não lista `verificar_entrega.py` nem `exportar_evidencias.py`.
- **Duração do roteiro:** o README diz "cinco minutos"; o roteiro diz até 4:50.

## Consistências confirmadas

- **Métricas:** todas as de `resultados.md`, README e roteiro batem com `evidencias_mlflow.json`, e as matrizes de confusão que reconstruí fecham. Conceito e controle têm os mesmos 535 positivos previstos; combinado e covariável, os mesmos 972.
- **Decomposição do Brier:** 0,021753 + 0,228136 = 0,249889.
- **Correção BH:** p ajustado / p bruto ≈ 14, coerente com 14 variáveis contínuas.
- **Horários:** a conversão UTC para São Paulo e a cronologia entre execução e verificação estão corretas.
- **Roteiro:** os blocos são contíguos até 4:50 e a estrutura STAR está completa.
- **Limites documentados:** alerta combinado e equidade descritiva são apresentados sem alegação de redução empírica de viés.

## Veredito

**Conformidade:** aprovação condicionada. As correções 04 são consistentes em UTF-8/pt-BR, causalidade, distinção entre as políticas de detecção e roteiro; os itens 1 a 3 exigem tratamento na versão analisada.

**Qualidade:** boa. A coerência numérica é alta e os limites são declarados com honestidade, mas a cadeia de evidências ainda tem os elos fracos dos itens 4 e 5.
