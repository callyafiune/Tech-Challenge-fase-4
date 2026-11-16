# Revisão adversarial — 03d-integridade-fechamento

Modelo solicitado: `fable`. Modelo retornado: `claude-fable-5-2`.

# Rechecagem 03d — itens 1 a 3 da 03c

Os três itens estão **CORRIGIDOS** e não há defeito crítico. Análise apenas por leitura do pacote: nada foi executado, e o único hash que conferi foi o SHA-256 de saída vazia dos comandos 4 e 5 (`e3b0c442…b855`, correto).

## Julgamento por item

| Item | Status | Base |
|---|---|---|
| (1) URI remota vira constante | **CORRIGIDO** | `_safe_tracking_uri` em `pipeline.py` devolve `"destino_remoto_omitido"` para tudo que não começa com `sqlite:`. Os 10 casos remotos e malformados dos testes exigem igualdade exata com a constante. |
| (2) Evidência da CLI rotulada como derivada e validada | **CORRIGIDO** | `codigo_saida: 0` saiu do registro. `command_reference` e `cli_exit_code` dizem "não capturado da CLI original" e `origem_do_status` diz "derivado". `validate_execution` confere ID contra o nome do diretório, status, config, manifesto contra resumo, cenários, cada hash do manifesto e a igualdade entre arquivos em disco e chaves do manifesto. |
| (3) Fonte comparada por bytes, sem `git_dirty` | **CORRIGIDO** | Só `files_sha256` e `source_sha256` são comparados. Há teste positivo com `git_dirty` divergente e dois negativos (`fonte`, `hash_fonte`). |

No item 2, a igualdade de conjuntos também barra caminhos não canônicos (`./x`, `a/../x`, `C:x`, diferença de caixa no Windows), e caminhos UNC absolutos são rejeitados antes de qualquer `resolve()`.

## Contagens conferidas

- **150 testes:** o log literal tem 72 + 72 + 6 pontos, com percentuais coerentes (48% e 96%) e "150 passed". Os 11 avisos fecham em 2 + 4 + 4 + 1.
- **17 hashes:** `artifacts_sha256` tem 17 entradas (4 cenários × 3, mais `alertas.json`, `index.html`, `logs.jsonl`, `modelo.joblib` e `resumo.json`).
- **Ruff:** `check --show-files` lista 26 arquivos (25 `.py` e `pyproject.toml`). O comando 7 lista 50 incluídos e 49 formatados, ou seja, 25 `.py` e 24 `.md`. Isso sustenta a observação sobre `.md` no JSON.
- **31 fontes, não 32:** 25 `.py` mais os 6 arquivos nomeados em `_source_identity` dão 31. O número 32 só aparece contando `pyproject.toml` duas vezes. Ressalva: `files_sha256` do resumo não veio no pacote, então 31 é derivado e supõe que os seis arquivos existam (`uv.lock` não aparece em nenhum trecho).
- **Sem contagem imposta:** nenhum 17, 31, 150 ou 49 está fixado no script nem nos testes.
- **Coerência cruzada:** `execution_id`, `source_sha256`, duração (28.096017), alertas (8) e drift por cenário batem entre `verificacao.json` e `evidencias_mlflow.json`. Os horários do MLflow caem dentro da janela da execução.

## Críticos

Nenhum.

## Importantes

**Os testes negativos de ID, status e escape não discriminam a checagem que dizem cobrir** (`tests/test_verificar_entrega.py`, `test_entrega_rejeita_inconsistencia_ou_adulteracao`).

- **ID e status:** os casos `id` e `status` alteram só o resumo. Se a linha `summary["execution_id"] != execution_dir.name or summary["status"] != "sucesso"` for apagada, os 10 casos continuam verdes, porque a divergência com o manifesto e o hash de `resumo.json` rejeitam do mesmo jeito.
- **Escape:** sem a checagem de confinamento, o caso `escape` continua verde pela igualdade de conjuntos, mas o arquivo externo passa a ser lido.
- **Impacto:** uma regressão futura aceitaria uma execução com falha coerente como evidência. Esse é exatamente o formato que `_persist` grava no caminho de erro (resumo e manifesto com `status: "falha"` e hashes consistentes). O mesmo vale para um diretório renomeado.
- **Correção:** usar `pytest.raises(ValueError, match=...)` com a mensagem de cada caso. Para ID e status, montar variantes coerentes: copiar a execução para um diretório com outro nome, e gravar `status: "falha"` em resumo e manifesto com o hash recalculado.

O código está correto; o defeito é só de cobertura.

## Menores

1. **Caminho pessoal em evidência versionada** (`scripts/verificar_entrega.py`, comando 7). O `--verbose` grava `C:\Users\Cally\.config\git/ignore` em `07-comando.log` e em `verificacao.json`. É regressão de privacidade deste diff, de baixo impacto. Correção: neutralizar o ambiente desse comando ou aceitar e documentar.
2. **`evidencias_adicionais_sha256` não amarra o conteúdo à execução.** `docs/evidencias_mlflow.json` é hasheado sem conferir `execution_id` e `source_sha256`, e é omitido em silêncio se faltar, mantendo "aprovado". Neste pacote os valores batem. Correção: validar os dois campos e falhar na ausência.
3. **Conjunto mínimo de artefatos não é exigido.** Um manifesto reduzido a `resumo.json` passa; a própria fixture tem 2 arquivos. A validação é de consistência interna, não de autenticidade. Correção: reutilizar a lista de `_verify_artifacts`.
4. **Config relida com `yaml.safe_load` em vez de `load_config`.** Se `load_config` passar a normalizar ou aplicar defaults, execuções legítimas serão rejeitadas. Falha fechada, então é só fragilidade.
5. **Manifesto lido duas vezes.** O `manifest_path.read_bytes()` do retorno fica fora do `try`: um `OSError` ali vira traceback, e o hash registrado pode não ser o dos bytes validados. Correção: hashear os bytes já lidos.
6. **Lacunas de cobertura.** Faltam casos para artefato listado e ausente, divergência de cenários (a fixture usa `scenarios: {}`), manifesto sem `artifacts_sha256` e `sqlite:` em maiúsculas. O teste de registro não afirma a ausência de `codigo_saida` em `execucao_real`.
7. **Bordas de `_safe_tracking_uri`.** Stores locais não SQLite (`file:`, caminho relativo) recebem o rótulo "remoto", o que é impreciso mas não vaza nada. Uma URI `sqlite://usuario:senha@host/x` seria preservada inteira; isso já existia antes do diff. Restringir a `sqlite:///` tornaria a propriedade estrita.
8. **Observação do Ruff é texto fixo no script.** Hoje o comando 7 a sustenta, mas ela não é derivada da saída.

## Não verificável neste pacote

- **Hashes:** não recalculei nenhum além do de saída vazia.
- **Arquivos ausentes:** `resumo.json`, `manifesto.json`, `pytest.xml`, `07-comando.log` e os `.md` não vieram. A explicação do Ruff em MD e a ausência de alegação de captura nos demais documentos ficam sem julgamento; só o JSON e o script foram vistos.
- **Staging:** o retrato do Git do início da sessão não mostra `docs/validacao/07-comando.log` no índice. Como o `verificacao.json` o referencia, ele precisa entrar no commit, quando autorizado, sem conversão de fim de linha.

## Veredito

- **Conformidade:** itens 1, 2 e 3 CORRIGIDOS. Não encontrei regressão funcional introduzida pelo diff, e o registro literal de 150 testes e as contagens 17, 49, 26 e 31 são coerentes entre si.
- **Qualidade:** aprovado com ressalvas. A ressalva relevante é a dos testes negativos de ID, status e escape; as demais são menores e não bloqueiam o fechamento da 03c.
