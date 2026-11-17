# Revisão adversarial — 08-docker

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão adversarial: contêiner do pipeline

Fiz apenas leitura estática do pacote, sem executar nada. Não encontrei defeito crítico confirmado, mas há cinco importantes, e a conformidade não pode ser atestada antes do build e do smoke. `pipeline.py`, `uv.lock`, `params.yaml`, `.gitattributes`, `.python-version` e o enunciado não vieram no pacote, então vazamento treino/teste e validade estatística ficaram fora do que pude avaliar.

## Críticos

Nenhum confirmado. O candidato a bloqueador é a existência das tags `python:3.11.18-slim-bookworm` e `ghcr.io/astral-sh/uv:0.11.6`, que não consegui confirmar. Se uma delas não existir, o build falha na primeira linha; confira com `docker manifest inspect`.

## Importantes

1. **Telemetria do MLflow fica ativa fora de `track_execution`** (`Dockerfile`, `docs/docker.md`, `tracking.py`).
   - **Defeito:** `MLFLOW_DISABLE_TELEMETRY` só é definido por `os.environ.setdefault` dentro de `track_execution`. O comando `--entrypoint mlflow ... ui` documentado nunca passa por ali.
   - **Impacto:** a UI sobe com a telemetria padrão do MLflow 3 e pode fazer tráfego de saída não declarado. A proteção do pipeline também depende de nenhum módulo importar `mlflow` antes dessa função.
   - **Correção:** definir `MLFLOW_DISABLE_TELEMETRY=true` e `DO_NOT_TRACK=true` no `ENV` do estágio final ou em `environment:` do Compose.

2. **`uv sync --frozen` não valida o lock contra o `pyproject.toml`** (`Dockerfile`).
   - **Impacto:** se o `pyproject.toml` mudar sem regenerar o `uv.lock`, a imagem é construída em silêncio com um conjunto de dependências divergente do declarado.
   - **Correção:** trocar por `--locked`, que falha nesse caso.

3. **Falhas no contêiner não são diagnosticáveis pelos logs** (`cli.py:main`).
   - **Defeito:** qualquer exceção vira "Execução interrompida." mais "Não foi possível identificar um diretório de evidências.".
   - **Impacto:** erro de permissão no volume, falha de download, certificado de proxy e `PackageNotFoundError` podem exigir a consulta ao diagnóstico estruturado da execução.
   - **Correção:** imprimir ao menos o nome da classe da exceção e a etapa, ou habilitar o traceback por variável de ambiente opcional.

4. **A UI do MLflow tem escrita sobre as evidências** (`docs/docker.md`, `tracking.py:track_execution`).
   - **Defeito:** o comando monta `artefatos` em leitura e escrita, então runs e experimentos podem ser apagados pela UI.
   - **Impacto:** excluir um experimento pode afetar a próxima execução; o comportamento de `get_experiment_by_name` para experimentos removidos no backend SQL requer verificação.
   - **Correção:** documentar o risco ou tratar experimento excluído em `track_execution`.

5. **A reprodutibilidade cobre só as dependências Python** (`Dockerfile`).
   - **Defeito:** as imagens base, o uv e o frontend `# syntax=docker/dockerfile:1` são referenciados por tag flutuante. A documentação admite isso para as imagens, mas não menciona o frontend.
   - **Correção:** fixar por digest (`@sha256:...`) ou registrar os digests efetivos do build junto às evidências.

## Menores

- **`/tmp` sem limite** (`compose.yaml`): o tmpfs não tem `size` e o serviço não tem limite de memória nem de PIDs. Arquivos temporários do MLflow e do Evidently consomem RAM do host; use `/tmp:size=...,mode=1777` e limites de recursos.
- **Sem bytecode** (`Dockerfile`): `PYTHONDONTWRITEBYTECODE=1`, sistema somente leitura e ausência de `UV_COMPILE_BYTECODE=1` fazem pandas, sklearn, mlflow e evidently serem recompilados em memória a cada execução. Compilar no build acelera o início, ao custo de imagem maior.
- **Execução sem rede não documentada** (`docs/docker.md`): o plano exige esse teste, mas não há comando nem override `network_mode: none`. O contêiner mantém saída de rede durante todo o pipeline, embora só precise dela no primeiro download.
- **Métricas duplicadas** (`tracking.py`): `finalize_tracking` registra `alertas`, `duracao_total_segundos` e `memoria_maxima_mb` e depois chama `sync_tracking_artifacts`, que registra as mesmas três. O histórico fica com dois pontos por métrica.
- **SIGTERM não tratado** (`cli.py`): `docker stop` encerra o processo sem passar pelo `except`, e o run MLflow fica como `RUNNING`.
- **Plano desatualizado** (`docs/plano_docker.md`):
  - Todas as caixas estão desmarcadas.
  - O primeiro passo ("verificar que o Dockerfile ainda está ausente") está obsoleto.
- **Afirmação imprecisa** (`docs/docker.md`): "escrita limitada aos volumes e ao `/tmp`" ignora `/dev/shm`. A cópia para o host também duplica modelo e HTML, que existem no diretório da execução e em `mlflow-artifacts`.
- **Cobertura**: não há teste automatizado nem script de smoke para o contêiner. A lista do plano é toda manual.

## A confirmar no build e no smoke

Estes pontos dependem de arquivos fora do pacote ou de comportamento que só a execução mostra:

- **Local do banco**: o pacote não mostra que o SQLite fica em `/app/artifacts/mlflow.db`. Se o caminho real for outro, o comando da UI cria um banco vazio em silêncio e mostra zero runs.
- **Diretório `/app/data/raw`**: não existe na imagem. O pipeline precisa criá-lo com `mkdir(parents=True)`.
- **Ausência de Git e de pacote instalado**: uma chamada a `git` por subprocesso ou a `importlib.metadata.version("confiabilidade-credito")` falharia, e o item 3 esconderia a causa.
- **`--no-build`**: aborta o build se alguma dependência transitiva só tiver sdist para Linux.
- **Finais de linha**: se o checkout no Windows tiver CRLF, `config_sha256` e o manifesto do contêiner diferem dos de um build feito a partir de checkout LF. Depende do `.gitattributes`.
- **`docker compose cp` com contêiner parado**: confirmar que o conteúdo do volume é copiado.
- **UI sob `read_only`**: confirmar que `mlflow ui` sobe sem tentar escrever em `/app`.
- **`artifacts/docker` ignorado pelo Git**: a documentação afirma, mas o `.gitignore` não veio.

## O que está correto na leitura

- **Volumes e usuário**: os volumes nomeados herdam a posse `10001` dos diretórios criados na imagem. O usuário é numérico, tem entrada em passwd e `HOME=/tmp` gravável.
- **Endurecimento**: `read_only`, `cap_drop: ALL`, `no-new-privileges` e `init` estão coerentes entre si.
- **Imagem final**: o venv é de root e imutável. Pela estrutura dos estágios, uv, cache e grupo dev ficam fora.
- **Contexto de build**: o `.dockerignore` por lista de permissão exclui dados, modelos e `.git`.
- **CLI e MLflow**: `ENTRYPOINT`/`CMD` batem com os argumentos da CLI e usam caminhos absolutos, que `artifact_root.as_uri()` exige. A porta da UI é publicada só no loopback.

## Veredito

- **Conformidade:** não atestável nesta rodada. O desenho é aderente ao escopo declarado (lote, sem API), mas falta evidência de build, de smoke com dados reais e da execução sem rede. O enunciado não veio no pacote, então a afirmação de que ele não exige contêiner nem API também não foi verificada.
- **Qualidade:** boa no desenho de segurança e no isolamento do contexto. Para aprovar, corrija os itens 1 a 3 e anexe a saída real do build e do smoke, incluindo a confirmação das tags.
