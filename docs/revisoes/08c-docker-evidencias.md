# Revisão adversarial — 08c-docker-evidencias

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão de fechamento: evidências Docker (pós-08b)

Revisão estática do pacote; não executei nada. Os logs 01–03, 06–07 e 09–17 e os de Ruff/formato não estão no pacote, então seus hashes e conteúdos não foram conferidos.

## Consistência conferida

- **Sequência:** os 17 comandos têm horários monotônicos, sem sobreposição, e a numeração bate com os arquivos.
- **Build único:** só há um `build`, e os `up` usam `--no-build`.
- **Identidade da imagem:** `e52e07fc…` aparece no log 04 (`exporting manifest list`), no log 05 (`Id`, `RepoDigests`, `Descriptor`) e em `imagem_executada`. `LastTagTime` e `Identity.Build.CreatedAt` (13:38:32.5) caem dentro da janela do build.
- **Bases:** os três digests de `bases_build` são os do log 04.
- **Execuções:** os IDs e as durações (82,94 s e 25,23 s) cabem nas janelas dos comandos `com-rede` e `sem-rede`.
- **Métricas:** recalculei precisão, recall, acurácia e prevalência a partir das matrizes de confusão dos quatro cenários e todas fecham, com 2.500 linhas cada. Os positivos previstos coincidem entre `control`/`concept` (535) e `covariate`/`combined` (972), como esperado quando só o rótulo muda.
- **Determinismo:** as duas execuções têm métricas e hashes de dataset, modelo e fonte idênticos.
- **Falha esperada:** saída 1 em projeto novo, com volumes recém-criados no log 08 e rede `none`; o diagnóstico aponta `aquisicao` com mensagem saneada.
- **Qualidade:** 150 pontos e 11 avisos no log do pytest, e 137,57 s é compatível com a janela de 142 s.
- **Documentação:** os números da tabela de `docs/docker.md` batem com o JSON.

## Críticos

Nenhum defeito crítico encontrado.

## Importantes

**I1. `docs/verificacao_docker.json` não é a saída do verificador versionado.**
- **Fato:** o JSON contém `qualidade` e `fim_verificador_utc`, que `scripts/verificar_docker.py` não grava. Além disso, `fim_utc` vale 13:44:08, quando o script o gravaria logo após `encerrar-ui` (≈13:41:50,5, valor que hoje está em `fim_verificador_utc`).
- **Fato:** `docker-qualidade.json` usa outro esquema (`sha256` em vez de `log_sha256`, sem `saida_esperada`), e seu coletor não está no pacote.
- **Fato:** a qualidade começou às 13:41:05,53, 0,7 s após `iniciar-ui` e 45 s antes do fim do verificador. Não foi "tudo em sequência", e isso contraria o "execute uma verificação por vez" do guia.
- **Fato:** há 40 s sem explicação entre o fim do pytest (13:43:28) e o `fim_utc` final.
- **Impacto:** o comando documentado não reproduz o arquivo publicado. Uma nova execução sobrescreve o JSON e apaga `qualidade`. A sobreposição não afeta as durações do pipeline, que terminou às 13:41:00, mas coincide com os 40 s de espera da UI.
- **Dúvida aberta:** não dá para saber se o script executado é o do pacote. Confira o SHA-256 atual de `scripts/verificar_docker.py` contra `3ed00845…`.
- **Correção:** versionar o coletor de qualidade, ou torná-lo etapa do verificador após `encerrar-ui`. O verificador deve gravar ele mesmo o vínculo ou não ter o JSON tocado depois. Em seguida, recolher uma vez, em série.

**I2. Logs não são literais em bytes e os hashes dependem do checkout.**
- **Fato:** em `executar()`, `log.write_text(conteudo, encoding="utf-8")` no Windows converte `\n` em `\r\n`. O mesmo vale para `destino` e `log_http`.
- **Fato:** os hashes (`log_sha256`, `ui.log_sha256`, `qualidade.sha256`, `arquivos_sha256`) são calculados sobre os bytes da árvore de trabalho.
- **Impacto:** se `.gitattributes` normalizar texto (o conteúdo dele não está no pacote), os hashes deixam de conferir após commit e checkout em outra plataforma. A evidência ficaria inverificável justamente quando for versionada.
- **Correção:** gravar `resultado.stdout` com `write_bytes`, marcar `docs/validacao/**` e os JSON de evidência como `-text`, e declarar a convenção de fim de linha dos fontes.

**I3. O build da coleta final veio inteiro do cache.**
- **Fato:** no log 04 todos os passos estão `CACHED`, em 3,5 s; a imagem tem `Created` 13:17:04Z, 21 minutos antes.
- **Impacto:** a coleta sequencial prova reuso de cache e identidade da imagem. Não mostra `uv sync --locked`, o download das bases nem o tempo de um build frio. Essa evidência só existe na primeira coleta, que tinha builds simultâneos.
- **Impacto:** a linha "Build concluído" e a frase "afetadas pelo armazenamento durante o build" sugerem mais do que a coleta atual mostra.
- **Correção:** declarar isso na tabela, apontando o log da primeira coleta como evidência do build frio, ou anexar um build `--no-cache` sequencial. Corrigir a frase dos tempos.

## Menores

1. **Vínculo imagem–contêiner parcial.** O `docker inspect` cobre só `…-pipeline-1` da execução sem rede. O contêiner com rede não é inspecionado antes do `up` sem rede (a mudança de `network_mode` tende a recriá-lo), e o do projeto `-sem-cache` também não é inspecionado. A sonda `imagem-sem-volumes` usa a tag, não `imagem["Id"]`. Correção: inspecionar após cada `up` e usar o ID no `docker run`.
2. **Exportação.** No modo `binario`, o stderr é capturado e descartado, e o SHA-256 do tar não é registrado. Só arquivos listados nos manifestos são conferidos; `mlflow.db` e os artefatos MLflow ficam fora.
3. **UI.** A checagem é só contagem e status. Os dez `run_id` não são comparados com `mlflow_pai`/`mlflow_filhos`, e o experimento `"1"` está fixo. O "log HTTP" é um resumo escrito pelo próprio verificador; `docker logs` do servidor não é capturado antes do `stop` com `--rm`.
4. **Sonda da imagem.** Ela confere só o primeiro nível de `/app`. Como `!src/**` admite qualquer arquivo, um dado ou binário sob `src/` passaria. Não há tentativa de escrita que prove o somente leitura, nem asserção de `CapDrop` e `no-new-privileges` no `inspect`.
5. **Robustez do verificador.**
   - Não limpa `docker-sequencial-*` antigos; uma falha no meio mistura coletas.
   - `TimeoutExpired` e erro de `decode` estrito ocorrem antes de gravar log e registro.
   - As verificações do host usam `assert`, que some com `-O`.
   - Falha em `encerrar-ui` dentro do `finally` mascara o erro original.
   - `arquivos_sha256` é calculado no fim, não antes do build, e cobre só `*.py` de `src/`.
6. **Resíduos.** Cada coleta deixa dois projetos com contêineres parados e quatro volumes. O guia não dá o comando de limpeza (`docker compose -p <projeto> down --volumes`), embora a política de retenção se aplique.
7. **Documentação.** O padrão `docs/validacao/docker-*.log` na seção "Verificação realizada" também casa com os logs da primeira coleta. O log do pytest expõe o caminho absoluto `C:\estudos\…`, sem dado pessoal; os `docker inspect` (logs 13 e 16, fora do pacote) provavelmente também expõem caminhos do host.

## Veredito

- **Conformidade:** mantida. Nada no pacote contradiz a aprovação anterior da implementação. Não há sinal de vazamento treino/teste nem de dados individuais nas evidências apresentadas.
- **Qualidade das evidências:** os achados centrais do 08b estão sanados (sequência, build único, identidade da imagem, falha esperada, exportação e UI).
- **Fechamento:** aprovado com ressalvas. Ele depende de I1, porque o JSON publicado não é o produto do script versionado e a qualidade rodou em paralelo com ele. I2 deve ser resolvido antes do commit. I3 se resolve com uma declaração explícita no guia.
