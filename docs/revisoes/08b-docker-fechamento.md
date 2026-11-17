# Revisão adversarial — 08b-docker-fechamento

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão adversarial: fechamento do bloco Docker

Não encontrei defeito crítico no Dockerfile, no Compose ou na CLI, mas as evidências não fecham: o log 02 contradiz o JSON de verificação em dois pontos (tempos e ID da imagem).

**Limites desta revisão:** nada foi executado e nenhum hash foi recalculado. Dos cinco logs, só `docker-02-com-rede.log` veio no pacote. Também ficaram fora `tracking.py`, `data.py`, `telemetry.py`, o README alterado e o parecer inicial; o que depende deles está marcado como não verificável.

## Críticos

Nenhum. Dockerfile, `.dockerignore`, Compose e CLI são coerentes entre si:

- **Estágios:** a contagem do Dockerfile bate com o log (5 passos em `dependencias`, 6 em `execucao`).
- **Banco MLflow:** `PROJECT_ROOT` resolve para `/app`, então o SQLite cai no volume `artefatos`.
- **Volumes:** os diretórios são criados e recebem `chown` antes da montagem, o que permite a escrita pelo UID 10001.

## Importantes

Os dois primeiros bloqueiam o fechamento das evidências, não a conformidade com o enunciado.

1. **Janela da etapa 02 incompatível com o próprio log** (`verificacao_docker.json` × `docker-02-com-rede.log`).
   - O log mostra passos sequenciais por dependência: `#16` 133,0 s, `#17` 131,1 s e `#20` 186,3 s, ou seja, pelo menos 450 s de build.
   - O JSON registra 311 s para a etapa inteira (13:17:59 a 13:23:10), incluindo os 111,89 s do pipeline.
   - O ID da execução (`20261117T132115`) põe o início do pipeline 196 s após o início da etapa.
   - Impacto: ou o `inicio_utc` está errado, ou o trecho de build do log não pertence à invocação cronometrada. A afirmação de "logs literais" não se sustenta.
   - Correção: reexecutar o roteiro inteiro de uma vez e regenerar JSON e logs juntos, ou explicar a origem do trecho de build.

2. **ID da imagem não aparece no log do build** (`verificacao_docker.json`, campo `imagem.id`).
   - O JSON registra `sha256:2d5072fd…`.
   - O log exporta manifest `6cd191d7…`, config `563bbdf2…`, attestation `31f7730c…` e manifest list `eb004e8d…`. Nenhum coincide.
   - Impacto: a imagem inspecionada na etapa 05 pode não ser a que rodou nas etapas 02 a 04, o que reforça o item 1.
   - Correção: conferir com `docker-05-imagem.log` e registrar o ID logo após o build, na mesma execução.

3. **Resultados sem comando, log ou hash.**
   - Os blocos `ui_mlflow`, `copia_conteiner_parado` e `bases_build` vêm depois de `fim_utc`, sem carimbo de tempo.
   - A linha "Suíte local" (150 testes, 11 avisos, Ruff) em `docs/docker.md` não tem nenhum registro.
   - O roteiro que gera o JSON não está entre os arquivos do repositório.
   - Não há prova de que o comando de UI documentado (raiz somente leitura, diretório de trabalho `/app`, sem `--default-artifact-root`) foi o que retornou HTTP 200.
   - Correção: registrar essas etapas no mesmo formato das cinco primeiras e versionar o roteiro.

4. **"Dados e arquivos privados do host ausentes" é mais amplo que o assert** (etapa 04; `docs/docker.md`, linha "Isolamento"; `docs/plano_docker.md`).
   - O assert só nega `.git`, `tests`, `docs` e `reports`.
   - A inspeção roda com os volumes montados, que mascaram `/app/data` e `/app/artifacts` da imagem. O conteúdo da imagem nesses caminhos nunca foi examinado.
   - A lista de permissões do `.dockerignore` torna o risco baixo, mas a verificação marcada com `[x]` não ocorreu como descrita.
   - Correção: inspecionar com `docker run --rm` sem volumes, comparando a listagem de `/app` com a lista esperada e exigindo `data/` e `artifacts/` vazios.

5. **Caminho de falha nunca exercitado no contêiner.**
   - O guia afirma que falhas são propagadas, que cache ausente impede a execução sem rede e que `failure.error_type` e `failure.failed_stage` ficam disponíveis. Só há execuções com saída zero.
   - Correção: rodar o override sem rede em um projeto Compose novo (`-p`), esperando saída 1 e `failed_stage == "aquisicao"`.

## Menores

- **Log 02 fora de ordem:** "Execução concluída" aparece antes de "Image … Building" e há um resíduo `[K`. Os fluxos de saída foram concatenados; vale declarar isso ou capturar com `2>&1`.
- **Hashes incompletos:** `arquivos_sha256` omite `src/`, `.python-version` e `.gitattributes`. A inspeção também não registra `source_sha256`, `model.sha256` nem o hash do dataset das duas execuções. Assim, "cache validado" e o vínculo entre imagem e repositório ficam só implícitos.
- **Exportação:** o registro traz apenas contagem e bytes (87 arquivos, 82 MB). "Conferido" pede comparação com `artifacts_sha256` do manifesto. O `docker compose cp` documentado não foi o comando testado, o que está declarado.
- **Sem lastro no pacote:** "1,38 GB", "Linux/amd64", "sem avisos na checagem" e "configurações válidas". Não há etapa `docker compose config`.
- **Threads:** `OMP_NUM_THREADS=1` e `OPENBLAS_NUM_THREADS=1` afetam tempo e determinismo, mas não constam na tabela de composição.
- **Limite de etapa:** `max_stage_seconds: 120` fica próximo dos 111,89 s totais da primeira execução. O comportamento de `check_health` em máquina mais lenta não é verificável sem `telemetry.py`.
- **Inspeção de uso único:** `assert len(sumarios) == 2` falha após uma terceira execução.
- **Versionamento:** todo o bloco está sem commit (`??`), o que pesa no requisito de histórico semântico.

## Limitações aceitas (não contadas como defeito)

- Tags sem digest fixo: os três digests de `bases_build` conferem com o log 02.
- Ausência de traceback, por privacidade.
- Interrupção por SIGTERM sem conclusão auditada.
- UI com permissão de escrita.
- Ausência de API e de bytecode compilado.

## Conferido e consistente

- As matrizes de confusão reproduzem acurácia, precisão, recall e prevalência nos quatro cenários.
- Os positivos previstos são iguais entre controle e conceito (535) e entre covariável e combinado (972), como exige o contrafactual.
- 22 eventos e 8 alertas batem com o fluxo de `pipeline.py`.
- Os tempos da etapa 03 e o horário do MLflow no log batem com o JSON.

## Veredito

- **Conformidade com o enunciado:** conforme. O contêiner executa o pipeline exigido e o Docker é um acréscimo que não introduz regressão.
- **Qualidade da implementação:** boa, aprovada.
- **Fechamento das evidências:** não aprovado nesta rodada. Os itens 1 e 2 precisam ser reconciliados com uma reexecução única do roteiro; os itens 3 a 5 são recomendados para que a tabela "Verificação realizada" corresponda ao que foi de fato executado.
