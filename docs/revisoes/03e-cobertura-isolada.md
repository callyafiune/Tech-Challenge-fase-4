# Revisão adversarial — 03e-cobertura-isolada

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão final: Important de cobertura 03d (casos negativos ID / status / escape)

Os três casos estão **CORRIGIDOS**: cada fixture agora isola o guard que pretende testar. A análise é estática, sobre o código colado; não executei nada, e os 12 testes aprovados são alegação do executor, não verificada aqui.

## Adjudicação por caso

### 1. ID do diretório: `test_id_do_diretorio_deve_corresponder_a_execucao_integra` — CORRIGIDO

- **Fixture:** `shutil.copytree` copia a execução inteira para `artifacts/outro-id`, sem alterar um byte de resumo, manifesto ou `index.html`. A única variável alterada é o nome do diretório.
- **Isolamento:** sem a comparação `summary["execution_id"] != execution_dir.name`, a cópia passa por todos os guards seguintes e a função retorna, então o teste falharia com "DID NOT RAISE". Os guards seguintes são fonte, config, manifesto contra resumo, cenários, hashes e conjunto de arquivos.
- **Mensagem:** `match="identidade"` só casa com a mensagem do guard de identidade/status; nenhuma outra mensagem, nem a genérica do `except`, contém o termo.
- **Controle positivo:** `test_mesmos_bytes_sao_aceitos_quando_apenas_git_dirty_muda` valida os mesmos bytes no diretório correto.

### 2. Status de falha coerente: `test_execucao_com_falha_coerente_e_hashes_validos_nao_comprova_sucesso` — CORRIGIDO

- **Fixture:** resumo e manifesto recebem `status = "falha"`, e o hash de `resumo.json` é recalculado a partir dos bytes regravados. O hash de `index.html` e o conjunto de arquivos continuam válidos.
- **Isolamento:** sem `summary["status"] != "sucesso"`, tudo o mais passa (ID, fonte, config, metadados do manifesto, cenários `{}`, hashes, `actual_files`) e a função retorna. Os guards de adulteração e de divergência manifesto/resumo não conseguem mascarar a ausência do guard de status.
- **Mensagem:** `match="sucesso"` só existe na mensagem desse guard.

### 3. Escape de caminho: `test_caminho_externo_e_rejeitado_antes_de_ler_seus_bytes` — CORRIGIDO

- **Fixture:** `../../externo.txt` resolve para `raiz/externo.txt`, que existe e está fora de `execution_dir`. O hash registrado é o correto, calculado antes do `monkeypatch`, então o guard de adulteração não mascara o resultado.
- **Espião:** `Path.read_bytes` é substituído na classe, e o original é capturado antes. A comparação por `resolve()` normaliza os `..`.
- **Guard removido ou movido para depois da leitura:** o espião lança `AssertionError`. Ela não está na tupla do `except` de `validate_execution` nem é capturada por `pytest.raises(ValueError)`, então o teste falha.
- **Sem o espião:** o guard de `actual_files` emitiria "fora do manifesto", que não casa com `match="fora da execução"`. O isolamento é duplo.
- **Leituras legítimas:** `resumo.json` e `index.html` passam pelo espião sem interferência, e as entradas legítimas são iteradas antes da externa.

## Críticos

Nenhum defeito encontrado.

## Importantes

Nenhum defeito encontrado. O Important de cobertura 03d está sanado nos três casos.

## Menores (residuais, não bloqueantes, sem reabrir desenho)

- **Espião acoplado à implementação (caso 3):** só `Path.read_bytes` é interceptado. Uma refatoração futura do helper para `open(path, "rb")`, `path.open()` ou `hashlib.file_digest` leria o arquivo externo sem disparar o espião. O `match` ainda detectaria a remoção do guard, mas não a leitura antecipada. Para o helper atual, que lê artefatos só via `path.read_bytes()`, a cobertura é efetiva.
- **Mensagem compartilhada (casos 1 e 2):** ID e status emitem a mesma mensagem, então `match="identidade"` e `match="sucesso"` casam com o mesmo texto. A discriminação vem das fixtures, não do `match`. Separar exigiria alterar o helper, fora do escopo desta rodada.
- **Evidência de execução:** a aprovação dos 12 testes deve ser comprovada por `docs/validacao/pytest.xml` e pelo log com hash em `docs/verificacao.json`, gerados sobre estes bytes. Esses arquivos não constam do pacote revisado.

## Veredito

- **Conformidade:** o Important de cobertura 03d está **CORRIGIDO** nos três casos (ID, status, escape), sem pendência em aberto neste item.
- **Qualidade:** boa. Cada fixture altera uma variável só e tem controle positivo; os residuais acima são apenas registro documental.
- **Ressalva:** o veredito vale para o código como colado e depende da evidência literal do executor para a execução.
