# Revisão adversarial — 03c-metadados-finais

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Revisão adversarial dos resíduos 03b

**Não encontrei defeitos críticos, mas dois dos seis resíduos estão só parcialmente corrigidos: a sanitização de URI e o registro da execução real.** Fiz apenas leitura estática do pacote, sem executar nada. Não pude conferir `telemetry.py`, `monitoring.py`, `.gitattributes`, `docs/validacao/*` nem os hashes, porque não vieram no pacote.

## Críticos

Nenhum.

## Importantes

1. **`pipeline.py:_safe_tracking_uri` ainda publica o usuário quando a senha tem `/`, `?` ou `#` sem codificação.**
   - **Causa:** a proteção depende de `parsed.port` lançar `ValueError`, o que só ocorre se o trecho após `:` não for numérico (ou for maior que 65535).
   - **Reprodução:** `postgresql://usuario:12/ss@host/banco`, `postgresql://usuario:/ss@host/banco` e `mysql://usuario:8080?x@host/db` resultam em `<esquema>://usuario`.
   - **Impacto:** o usuário do banco vai para `resumo.json`, `manifesto.json` e os artefatos do MLflow; a senha não vaza. Até onde sei, o SQLAlchemy aceita `/` na senha, então são URIs funcionais.
   - **Correção:** omitir o host quando o netloc tiver `:` sem `@` e houver `@` no restante da URI. Os dois testes atuais continuam passando; `https://host:8080/pasta@x` perde o host, o que é aceitável.
   - **Teste:** parametrizar com os três casos acima; o teste atual só cobre prefixo não numérico (`pa/ss`).

2. **`scripts/verificar_entrega.py`: o bloco `execucao_real` é declarado, não literal.**
   - **Campos fixos:** `comando` e `codigo_saida: 0` são constantes do script; nada foi capturado da execução.
   - **Sem vínculo:** o script não confere se `--resumo` está em `artifacts/<execution_id>/` nem se `config_sha256` corresponde ao `params.yaml` atual.
   - **Sem integridade:** ele grava `manifesto_sha256`, mas não recalcula os `artifacts_sha256` do manifesto. Um `resumo.json` editado após a execução seria aceito, e `alertas` e `drift_por_cenario` sairiam do arquivo editado.
   - **Correção:** executar o pipeline dentro do verificador capturando saída e código, ou rotular os campos como derivados do resumo e validar manifesto, arquivos, caminho e configuração.

3. **`verificar_entrega.py`: a comparação `_source_identity() != summary["source"]` inclui `git_dirty`.**
   - **Impacto:** se a execução validada partiu da árvore suja que o git status mostra, ela é rejeitada pelo próprio verificador após o commit, mesmo com arquivos idênticos.
   - **Agravante:** o único commit é `22313dd`, e os fontes aparecem apenas como adicionados no índice. Se o `git_revision` do resumo for esse, ele aponta para um commit sem o código, e `source_sha256` é o único vínculo real.
   - **Correção:** comparar apenas `files_sha256`, manter `git_dirty` como informação e regenerar a evidência após o versionamento das fontes.

4. **Cobertura: as correções de identidade e de registro não têm teste de regressão no pacote.**
   - Nada em `tests/test_pipeline.py` afirma que `scripts/*.py`, `ci.yml`, `.python-version` e `.gitattributes` entram em `files_sha256`, nem que alterá-los muda `source_sha256`.
   - Não há teste de `verificar_entrega.py` rejeitando fonte divergente ou execução com falha.

## Menores

- **Falha esperada por estágio, não por tipo de exceção** (`_contract_demo`; depende de `telemetry.py`): uma exceção diferente de `DataContractError` dentro de `contrato_invalido_*` é filtrada como esperada. O resultado é `failed_stage="pipeline"`, com a origem real mascarada.
- **Cartão do relatório** (`reporting.py`): numa falha fora de estágio, o HTML mostra Estado "falha" com "Falhas inesperadas: 0". O `failed_stage` não aparece no relatório.
- **Rótulos**:
  - O fallback `label_names.get(x, x)` deixa passar valores em inglês não mapeados.
  - O teste usa um resumo sintético, e o teste de integração não verifica o HTML real.
  - A tag MLflow `rotulos` continua com o valor bruto.
- **Runs filhos**:
  - `relatorio_run_pai` duplica `mlflow.parentRunId`; apontar para `observabilidade/<cenário>/evidently.html` seria mais útil.
  - Os filhos ficam `FINISHED` quando o pai é marcado `FAILED`.
  - `evidencias_mlflow.json` não lista os artefatos dos filhos, então a ausência de HTML na execução real só é sustentada pelo teste.
- **Identidade** (`_source_identity`):
  - O hash de bytes brutos varia entre CRLF e LF se `.gitattributes` não fixar `eol`.
  - Arquivos ausentes, como `uv.lock`, são omitidos em silêncio.
  - Uma instalação não editável geraria identidade vazia sem erro.
  - O verificador não refaz a checagem ao final, e `uv run` sem `--locked` pode alterar `uv.lock`.
- **Registro literal** (`docs/verificacao.json`):
  - `ruff format` relata 46 arquivos, mas `--show-files` lista 25; a diferença não está explicada.
  - `pytest -q` não nomeia os testes, e `pytest.xml` não tem hash no registro.
  - Há caminhos absolutos `C:\estudos\...` no registro: não são dado pessoal, mas não são portáveis.
- **URI SQLite**: o caminho absoluto local é publicado e, em outro ambiente, pode conter o nome do usuário do sistema operacional. URIs que não são URL viram `://` ou `c://`.

## Conferido sem defeito

- **URI:** os dois casos dos testes (`usuario:pa/ss@host` e `host/pasta@SEGREDO`) produzem a saída esperada; query e fragmento são removidos.
- **`failed_stage`:** o filtro exclui falhas esperadas e cai em `"pipeline"`; o teste falharia no código anterior.
- **Rótulos:** `original_labels` vira "observados" no relatório.
- **Runs filhos:** recebem só `estatisticas.json` e a tag do pai; os quatro `relatorio_run_pai` da evidência coincidem com o `run_id` do pai.
- **Identidade:** cobre `src`, `tests`, `scripts`, `params.yaml`, `pyproject.toml`, `uv.lock`, `.python-version`, `.gitattributes` e `ci.yml`.
- **Consistência interna das evidências:**
  - `execution_id`, `source_sha256`, duração (25,397426 s) e alertas (8) batem entre os dois JSON.
  - Os 8 alertas são coerentes com a lógica de `_scenario_alerts`.
  - Os 134 testes batem com a contagem de pontos na saída.
  - O hash das saídas vazias é o SHA-256 de conteúdo vazio.
  - A ordem temporal entre execução e verificação é plausível.

## Veredito

- **Conformidade:** quatro resíduos estão corrigidos (`failed_stage`, rótulos, runs filhos, composição da identidade). Dois estão parciais: URI (item 1) e registro da execução real (itens 2 e 3).
- **Qualidade:** boa, **aprovado com ressalvas**. Os itens 1 a 3 são correções pequenas e devem entrar antes do fechamento. A evidência final precisa ser regenerada após o versionamento das fontes.
