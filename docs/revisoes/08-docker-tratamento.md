# Tratamento da revisão do bloco Docker

Parecer: [08-docker.md](08-docker.md), análise estática com Claude Code (`claude-fable-5-2`). A primeira rodada foi estática e antecedeu os testes de integração.

| Achado | Tratamento |
|---|---|
| Telemetria da UI não coberta pela função de tracking | Variáveis de desativação definidas no estágio final do Dockerfile, inclusive para comandos com outro entrypoint. |
| Divergência silenciosa entre projeto e lock | Instalação alterada para `uv sync --locked`; divergência deve impedir o build. |
| Diagnóstico sem traceback na CLI | Política de privacidade preservada. O pipeline já persiste classe e etapa em `failure.error_type` e `failure.failed_stage`; o guia explica como recuperar esses campos e reconhece falhas anteriores à criação das evidências. Não foi introduzida publicação de exceções com valores individuais. |
| UI pode modificar evidências | Guia declara a permissão de escrita, os efeitos da exclusão de runs/experimentos e a necessidade de preservar registros ou backups. A UI é opcional e publicada somente no loopback. |
| Tags e frontend podem mudar | Limite declarado no guia; digests efetivamente usados registrados na verificação da imagem e conferidos contra o log do build. Não se promete build bit a bit a partir de tags. |
| Diretório temporário sem limite | `/tmp` limitado a 512 MiB no Compose. |
| Sem comando de execução isolada da rede | Adicionado `compose.sem-rede.yaml`, reutilizando os volumes com `network_mode: none`. |
| Interrupção por SIGTERM | Limite documentado: interromper não equivale a conclusão auditada; estados e evidências precisam ser conferidos. Não se alterou o ciclo de vida do pipeline neste bloco. |
| Bytecode e registro repetido de métricas | Compilar bytecode aumentaria a imagem; o histórico de métricas preexistente não foi alterado. Nenhum dos dois impede a execução do contêiner. |
| Arquivos omitidos do pacote de revisão | O smoke real verificou caminhos, SQLite, permissões, cache, HTML e ausência de dependências de desenvolvimento. A rodada de fechamento inclui enunciado, pipeline e evidências observadas. |

As verificações e seus resultados estão consolidados em [verificacao_docker.json](../verificacao_docker.json). O parecer inicial não constitui certificação de execução; o estado efetivo é o registrado pelos comandos concluídos. Duas execuções completas, incluindo uma com `network_mode: none`, terminaram com saída zero e métricas idênticas; a UI retornou HTTP 200 e dez runs finalizados. A cópia a partir do contêiner parado também foi conferida, em memória.

## Correções após a revisão de fechamento

O [parecer 08b](08b-docker-fechamento.md) aprovou a implementação e a aderência ao enunciado, mas rejeitou o fechamento das evidências. A primeira coleta ocorreu durante dois builds simultâneos: o BuildKit compartilhou eventos de progresso, com tempos iniciados antes do comando capturado, e os índices OCI mudaram entre as exportações. Os streams textuais também estavam concatenados, sem preservar sua ordem conjunta. A [coleta original](../verificacao_docker_primeira_coleta.json) foi preservada; ela não é a referência final de duração e identidade da imagem.

Foi criado o [verificador reproduzível](../../scripts/verificar_docker.py), que executa os comandos em sequência e:

- Faz um único build, registra a imagem imediatamente e exige que seu ID apareça no log e seja o ID do contêiner executado.
- Registra stdout e stderr textuais em um único fluxo, horários e hashes dos logs.
- Inspeciona a imagem sem volumes, exige os diretórios de dados e artefatos vazios e confere o conteúdo de `/app`.
- Testa cache vazio com rede bloqueada, esperando saída 1 e falha na etapa `aquisicao`.
- Usa projetos novos por coleta, preserva os volumes usuais e compara duas execuções bem-sucedidas.
- Confere SHA-256 dos artefatos exportados contra os manifestos, registra hashes de código/configuração e verifica os runs pela UI com horários e log HTTP.

Os testes unitários do pipeline permanecem uma verificação separada. O verificador é exercitado de ponta a ponta com Docker real; nenhuma aprovação foi inferida apenas da leitura estática do script.

## Ressalvas da rodada 08c

O [parecer 08c](08c-docker-evidencias.md) confirmou a correção dos achados centrais da coleta anterior e manteve a aprovação da implementação, com ressalvas documentais:

- **I1 — saídas de coletores distintos:** o índice do Docker foi restaurado à saída exclusiva de `scripts/verificar_docker.py`, inclusive seu horário original de término; o hash desse script confere com o registrado na execução. A suíte local passou a ter coletor versionado próprio, `scripts/verificar_qualidade.py`, índice independente e nova execução posterior à conclusão do Docker. O coletor de qualidade não altera o índice do Docker.
- **I2 — convenção textual e Git:** o guia declara UTF-8/CRLF para a captura textual no Windows e distingue esses arquivos da captura em bytes do coletor de qualidade. O `.gitattributes` já contém `* -text`. A [checagem de preservação](../validacao/docker-preservacao-bytes.json) confirmou `text: unset` e igualdade dos objetos Git com e sem filtros, para log, índice e fonte do verificador. Os hashes protegem os bytes gravados e preservados pelo Git.
- **I3 — build com cache:** a tabela agora declara explicitamente que a coleta sequencial reutiliza camadas. A instalação efetiva permanece identificada na primeira coleta; seus tempos sobrepostos não são apresentados como benchmark de build frio. Os tempos publicados são os do pipeline.

Os volumes de diagnóstico são preservados, e o guia informa como removê-los por nome de projeto. As validações da UI são por HTTP, sem alegação de inspeção visual manual. A verificação criptográfica da exportação abrange os 34 artefatos declarados nos manifestos; o SQLite é validado pelas consultas e estados dos runs, sem alegar hash do arquivo de banco na exportação.
