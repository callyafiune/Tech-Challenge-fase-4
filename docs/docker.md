# Execução com Docker

[Voltar ao README](../README.md).

## Escopo

O [enunciado](enunciado.md) pede validação, treino do classificador, simulação e detecção de drift, relatórios e rastreamento. Não exige API HTTP nem serviço contínuo. O contêiner executa a CLI existente e encerra quando o pipeline termina; o resultado permanece em volume. O modelo é treinado dentro do contêiner, sem carregar modelos binários do host.

## Executar

Pré-requisito: Docker com suporte a contêineres Linux e Docker Compose v2. Não é necessário instalar Python ou uv no host. Execute na raiz:

Reserve espaço físico no host também para download, cache e estágios de build: eles consomem mais disco temporário que a imagem final. O espaço livre medido pelo pipeline dentro do contêiner pode representar o disco virtual do Docker; acompanhe separadamente a unidade que armazena esse disco virtual.

```powershell
docker compose up --build --abort-on-container-exit --exit-code-from pipeline
```

A primeira execução baixa a base pública UCI por HTTPS. O cache tem integridade validada e é reutilizado nas próximas execuções. O build também precisa acessar os registros das imagens e o índice das dependências. As execuções geram novos diretórios, preservando os resultados anteriores. Código de saída zero indica sucesso; falhas são propagadas pela CLI.

| Volume | Caminho no contêiner | Conteúdo |
|---|---|---|
| `dados` | `/app/data` | Cache da base UCI. |
| `artefatos` | `/app/artifacts` | Modelo, HTML, logs, alertas, métricas, banco SQLite e artefatos MLflow. |

Os nomes efetivos dos volumes recebem o prefixo do projeto Compose. Não são os diretórios `data/` e `artifacts/` do host. Nenhuma porta é publicada na execução padrão.

Depois de completar a primeira execução, é possível repetir o fluxo sem acesso à rede:

```powershell
docker compose -f compose.yaml -f compose.sem-rede.yaml up --abort-on-container-exit --exit-code-from pipeline
```

O override conserva os mesmos volumes e aplica `network_mode: none`. Cache ausente ou corrompido impede a execução; essa opção não substitui o primeiro download nem o build da imagem.

## Consultar os resultados

Depois da execução, copie os artefatos para o diretório local ignorado pelo Git:

```powershell
New-Item -ItemType Directory -Force artifacts/docker | Out-Null
docker compose cp pipeline:/app/artifacts/. ./artifacts/docker/
```

Abra `artifacts/docker/ID_DA_EXECUCAO/index.html`. O identificador é impresso pela CLI e os relatórios Evidently ficam nas quatro subpastas da execução. Os caminhos MLflow gravados no contêiner são caminhos Linux; copiar o SQLite para o host não reescreve suas URIs de artefatos.

Para abrir a UI MLflow com os volumes originais e resolver seus artefatos corretamente:

```powershell
docker compose run --rm -p 127.0.0.1:5000:5000 --entrypoint mlflow pipeline ui --backend-store-uri sqlite:////app/artifacts/mlflow.db --host 0.0.0.0 --port 5000
```

Acesse `http://127.0.0.1:5000`. A porta é publicada apenas no loopback do host. Encerre com `Ctrl+C`.

A UI tem permissão de escrita no banco e nos artefatos. Excluir runs ou experimentos altera as evidências e pode impedir a próxima execução; preserve esses registros ou faça backup antes de modificá-los.

## Composição da imagem

| Decisão | Efeito |
|---|---|
| Python 3.11.18 slim Bookworm | Base reduzida, compatível com as distribuições binárias das bibliotecas científicas. |
| Instalação em estágio intermediário | uv 0.11.6 e cache de instalação ficam fora do estágio final. |
| `uv sync --locked --no-dev --no-install-project --no-editable --no-build` | Confere a consistência de `uv.lock` com o projeto, sem ferramentas de desenvolvimento, instalação duplicada ou compilação de dependências. |
| `.dockerignore` com lista de arquivos permitidos | Exclui dados, modelos, Git, ambiente virtual, documentação, testes e relatórios históricos do contexto. |
| Código em `/app/src` | Mantém a CLI e permite registrar os arquivos realmente presentes no manifesto. |
| Usuário `10001:10001` | Pipeline não executa como root. |
| Sistema de arquivos somente leitura | Código e dependências imutáveis; volumes para persistência, `/tmp` temporário de até 512 MiB e dispositivos temporários do Docker. |
| Um processo de execução | Não inicia servidor de API, UI MLflow ou banco externo por padrão. |

Evidently, MLflow, Pandera e scikit-learn permanecem porque são usados no fluxo exigido. Suas dependências transitivas declaradas não são removidas manualmente. A variante slim reduz a base; ela não elimina o custo das bibliotecas científicas e dos relatórios.

As tags das imagens fixam versões, mas não seus digests; um novo build pode receber atualizações da base ou do frontend `docker/dockerfile:1`. O lock fixa as dependências Python. O manifesto do contêiner difere do histórico do host porque não inclui testes, scripts ou metadados Git. Métricas e verificações funcionais são os critérios de comparação entre plataformas.

## Diagnóstico de falhas

Use `docker compose logs pipeline` para identificar o diretório de evidências e copie os resultados. Em `resumo.json` ou `falha.json`, `failure.error_type` e `failure.failed_stage` identificam a classe e a etapa da falha sem divulgar valores de clientes. Falhas anteriores à criação desses arquivos podem exigir verificar espaço, volumes, configuração e conectividade. Mensagens brutas e tracebacks não são publicados pela CLI por privacidade.

Uma interrupção forçada ou `docker stop` não equivale a conclusão auditada. Pode deixar evidências incompletas e um run MLflow em andamento; confira o resumo, o código de saída e os estados no banco antes de considerar a execução válida.

## Encerrar e limpar

```powershell
# Remove o contêiner e a rede, preservando dados e resultados.
docker compose down
```

`docker compose down --volumes` também apaga os volumes de cache, modelos, relatórios e SQLite deste projeto. Use essa opção somente quando quiser descartar esses resultados.

A [política de retenção](governanca.md) também se aplica aos volumes, cópias exportadas e backups. Remover volumes não apaga as cópias que já foram feitas para o host.

## Verificação realizada

Execuções em 17/11/2026, Linux/amd64, registradas em [verificacao_docker.json](verificacao_docker.json), com capturas textuais UTF-8 em `docs/validacao/docker-sequencial-*.log`. Os hashes correspondem aos bytes dos arquivos gravados. No Windows, o coletor Docker usa CRLF; o `.gitattributes` do repositório desativa a conversão automática de texto (`* -text`), preservando esses bytes no Git. O tamanho compactado corresponde ao campo de conteúdo do Docker; o uso em disco inclui as camadas descompactadas e não inclui os volumes de resultados.

| Verificação | Resultado observado |
|---|---|
| Build e Compose | Coleta sequencial com camadas reutilizadas do cache; Dockerfile sem avisos na checagem; configurações normal e sem rede válidas. |
| Conteúdo compactado | Aproximadamente 287 MB; uso local da imagem: 1,38 GB, conforme Docker Desktop. |
| Execução com rede | Base UCI de 30.000 linhas; 82,94 s; 22 eventos e oito alertas; saída zero. |
| Repetição sem rede | Cache validado; 25,23 s; métricas dos quatro cenários idênticas; saída zero. |
| Qualidade e relatórios | Lotes inválidos bloqueados; quatro cenários e HTMLs existentes, com links locais válidos. |
| Falha com cache vazio e sem rede | Saída 1, diagnóstico estruturado na etapa `aquisicao`, em projeto separado. |
| Rastreamento | Dois runs pais e oito filhos, todos `FINISHED`; dez runs consultados pela UI HTTP. |
| Isolamento | UID 10001; código somente leitura; pytest, Ruff e uv ausentes. Inspeção sem volumes exige `data/` e `artifacts/` vazios e confere a lista de arquivos de `/app`. |
| Exportação | 34 hashes de artefatos conferidos contra os manifestos, por cópia do contêiner parado para tar em memória. |
| Suíte local do pipeline | 150 testes passaram; 11 avisos de depreciação de dependências; Ruff e formatação aprovados. [Coleta independente](validacao/docker-qualidade-final.json). |

Os tempos são medições do pipeline nesta máquina e dependem de cache, rede e recursos disponíveis, sem promessa de desempenho de produção. A instalação efetiva das dependências está registrada na primeira coleta, em `docker-02-com-rede.log`; seus tempos de build não são usados como referência final, pois havia builds simultâneos. A coleta sequencial valida a imagem já construída e não mede um build frio. A exportação para tar em memória evitou duplicar os artefatos no disco local durante a checagem.

Para repetir a coleta de evidências, com Python/uv no host:

```powershell
uv run python -X utf8 scripts/verificar_docker.py
```

O verificador executa um único build e vincula seu ID à imagem inspecionada e ao contêiner executado. Cada comando registra horários, saída e log com hash; stdout e stderr textuais são reunidos em ordem de emissão. Ele usa projetos Compose novos para não alterar os volumes usuais, testa a falha com cache vazio e rede bloqueada, valida os hashes do manifesto na exportação e consulta a UI por HTTP. Os nomes dos projetos ficam no JSON; os volumes são preservados para inspeção. A UI temporária é encerrada ao final, e a porta 5000 precisa estar livre.

Execute um verificador Docker por vez e evite outros builds simultâneos para a tag `credito-monitorado:local`. A suíte local é uma coleta independente, com índice próprio e logs preservados em bytes, sem alterar o JSON do Docker:

```powershell
uv run python -X utf8 scripts/verificar_qualidade.py
```

Para remover os contêineres e volumes de uma coleta, após inspecionar seus resultados, execute `docker compose -p NOME_DO_PROJETO down --volumes` e repita com o sufixo `-sem-cache`. Esses comandos descartam os dados da coleta indicada; os nomes estão em `verificacao_docker.json`.

A [primeira coleta](verificacao_docker_primeira_coleta.json) e seus logs foram preservados para rastrear os achados da revisão: houve builds simultâneos, com eventos compartilhados pelo BuildKit. Para tempos e identificação da imagem, use a coleta sequencial atual em `verificacao_docker.json` e os logs `docker-sequencial-*`.

## Referências técnicas

- [Boas práticas de build do Docker](https://docs.docker.com/build/building/best-practices/).
- [Integração do uv com Docker](https://docs.astral.sh/uv/guides/integration/docker/).
- [Persistência de modelos scikit-learn](https://scikit-learn.org/stable/model_persistence).
