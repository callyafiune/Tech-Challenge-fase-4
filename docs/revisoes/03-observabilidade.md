# Revisão adversarial — 03-observabilidade

Modelo solicitado: `fable`. Modelo retornado: `claude-fable-5-2`.

# Revisão adversarial: pacote `credito_monitorado`

Revisão estática: nada foi executado e o pacote não traz nenhuma evidência de execução (saída de testes, artefatos, relatório). Faltam `contracts.py`, `data.py`, `drift.py`, `model.py`, `monitoring.py`, `config.py`, `params.yaml`, `pyproject.toml`, o README e o roteiro.

## Críticos

Nenhum defeito crítico comprovável no código fornecido. A ressalva é de escopo: os módulos que sustentam 50% da nota (contratos e drift) não estão no pacote.

## Importantes

1. **`pipeline.py::_contract_demo`: a demonstração pode passar pelo motivo errado.**
   - O lote-base válido nunca é validado (sem controle positivo), e o `except DataContractError` não confere qual regra falhou.
   - Atribuir `np.nan` a `limit_bal` pode mudar o dtype da coluna, de modo que o bloqueio "nulo" pode vir do tipo, não da regra de nulos.
   - `"inference_calls": 0` é um literal, não uma medição. O teste que troca `pipeline.predict` é tautológico, pois a função nunca chama `predict`.
   - Impacto: o critério de 25% fica sem prova de que cada regra atua isoladamente.
   - Correção: validar o lote-base com sucesso, registrar e conferir a regra violada em cada variante e contar as chamadas de inferência de fato.

2. **`pipeline.py::_git_revision`: proveniência sem indicador de árvore suja.**
   - O manifesto grava apenas o `HEAD`, sem indicar alterações não commitadas.
   - No estado do repositório no início desta sessão (fora do pacote), `src/`, `tests/` e `params.yaml` estavam não rastreados, com um único commit. Uma execução nesse estado é atribuída a um commit que não contém o código.
   - Esse mesmo estado não atende a "histórico de commits semântico e organizado".
   - Correção: gravar `git status --porcelain` e o hash do `uv.lock` no manifesto.

3. **`pipeline.py::_safe_tracking_uri`: credenciais vazam em esquemas não HTTP.**
   - Só `http`/`https` são sanitizados. Com `--tracking-uri postgresql://user:senha@host/db`, a senha vai para `resumo.json` e `manifesto.json`, e ambos são enviados ao MLflow.
   - `output_dir` e a URI sqlite padrão também publicam caminhos absolutos locais.
   - Correção: remover userinfo e query de qualquer esquema e publicar caminhos relativos.

4. **Alegações fixas no código em vez de medidas.**
   - `"trained_only_on": "train"` é um literal, mas `train_baseline` recebe também `validation`.
   - Em `reporting.py`, "Treino 50% · validação 15%…", "Modelo avaliado fora do treino" e a lista de atributos excluídos são texto estático.
   - O pipeline grava hashes de IDs, mas não verifica que as partições são disjuntas.
   - Correção: derivar os textos de `summary["partitions"]` e de `FEATURES`, e falhar se houver interseção de `record_id`.

5. **`pipeline.py::_scenario_alerts`: alerta "crítico" sem incerteza.**
   - `QUEDA_AUROC` e `AUMENTO_BRIER` comparam estimativas pontuais de amostras diferentes, não pareadas (referência e lote).
   - Só `compare_concept` devolve intervalo de confiança; não há estimativa da taxa de falso alarme no controle.
   - O run pai do MLflow e o HTML mostram apenas `validation_metrics`, de um conjunto que também participa do ajuste, e não `reference_metrics`.
   - Correção: usar bootstrap da diferença e publicar as métricas da referência e os deltas na tabela de cenários.

6. **`reporting.py`: duas fontes de verdade para drift.**
   - O próprio relatório admite que o Evidently tem "decisões brutas" diferentes da política PSI/KS-BH usada nos alertas.
   - Impacto: o avaliador pode abrir o HTML do Evidently e ver variáveis diferentes das do painel, e o enunciado pede a identificação via Evidently.
   - Correção: configurar o Evidently com os mesmos testes e limiares, ou mostrar as duas decisões lado a lado.

7. **Auditoria de grupos invisível e sem mitigação.**
   - `summary["fairness"]` não aparece no `index.html`, no MLflow nem no manifesto.
   - Só há gap de aprovação, sem gaps de TPR/FPR, intervalos, limiar ou alerta.
   - Pelo texto do relatório, idade não está entre os atributos excluídos, mas é auditada como dimensão sensível.
   - A supressão olha o total do grupo, não o número de positivos e negativos que formam o denominador de TPR/FPR.
   - Impacto: "mitigação de vieses" (critério de 15%) fica sem evidência visual.

8. **Caminho de falha frágil (`run_pipeline`, `Telemetry.stage`).**
   - O fallback `write_json(resumo.json)` repete a operação que acabou de falhar. Se falhar de novo, substitui a exceção original e deixa em disco um resumo "em_execucao".
   - Falhas em `_persist`, `_verify_artifacts`, `check_health` e `finalize_tracking` ocorrem fora de qualquer estágio. O resumo manda "consultar etapas", mas nenhuma etapa aparece como falha.
   - `stage` só captura `Exception`: um Ctrl+C grava o evento como "sucesso" e não gera resumo.
   - Correção: gravar `failed_stage`, usar um fallback mínimo e sanitizado e tratar `BaseException` no estágio.

9. **Aderência à Etapa 2: não há dimensão temporal.**
   - São quatro lotes estáticos, sem janelas, sem `step` no MLflow e sem degradação progressiva, embora o enunciado peça "passagem do tempo".

## Menores

- **`tracking.py`:**
  - `artifact_root` e `PROJECT_ROOT` usam `parents[2]`, que ignora `--output` e quebra em instalação não editável.
  - Os links do `index.html` enviado ao MLflow ficam quebrados, pois os HTMLs do Evidently estão nos runs filhos.
  - Hiperparâmetros não são registrados como parâmetros, e a tag `UCI-350` é fixa.
  - Em falha, os runs filhos permanecem `FINISHED`.
- **`telemetry.py`:**
  - `disk_usage(anchor)` mede a raiz, não o volume de saída, em POSIX.
  - Os alertas de `check_health` não trazem valor observado nem limite, e o limite de disco é fixo.
  - `severity` é texto livre: o teste usa `"high"` e `QUEDA_AUC`, fora do vocabulário do pipeline.
- **`reporting.py`:**
  - `_number` formata booleanos como `1.0000`.
  - A tabela de alertas omite valor observado, limite e horário.
  - `concept_combined` é calculado e nunca exibido.
  - Limiar e valores de configuração entram no HTML sem formatação nem escape.
- **`pipeline.py`:**
  - O hash informado no `manifest.json` de origem é sobrescrito, não comparado.
  - A porta de 0,65 de AUROC é fixa no código.
  - `features_sha256` depende da ordem das linhas, ao contrário dos outros hashes.
  - `class_rate` vira NaN se o alvo vier todo nulo, o que derruba `write_json`.
  - O `index.html` fica fora dos hashes do manifesto.
- **`fairness.py`:** idades abaixo de 19 e códigos de sexo fora de 1/2 ficam fora de todos os grupos, sem aviso.
- **`cli.py`:** a mensagem de falha não informa o diretório da execução e aponta para um resumo que pode não existir.
- **`ci.yml`:**
  - `--frozen` em vez de `--locked`.
  - Actions fixadas por tag, sem bloco `permissions`.
  - Só Linux, embora o desenvolvimento seja em Windows.
  - `push` e `pull_request` duplicam execuções.
  - Sem medição de cobertura nem publicação do relatório HTML.

## Cobertura de testes

- Nenhum teste do pacote chega a `status == "sucesso"`.
- `tracking.py`, `cli.py`, `_scenario_alerts`, `_safe_tracking_uri`, `check_health` e `_verify_artifacts` não têm teste. O conteúdo do `index.html` não é verificado.
- Falta o teste de aceitação central: covariate e combined disparam `DRIFT_ENTRADAS`, e control não dispara.
- Não há teste de determinismo (duas execuções, mesmos hashes).
- O caminho `ROTULOS_PENDENTES` não é exercitado.
- Não dá para saber se o marcador `integracao` roda no CI, pois isso depende do `pyproject.toml`.

## Não verificável neste pacote

- Uso de Pandera e as três regras rígidas.
- Simulação de pelo menos duas variáveis e uso efetivo do Evidently.
- Vazamento no pré-processamento e na escolha do limiar.
- Se o contrato é aplicado à ingestão real: em `run_pipeline`, o estágio `validacao_origem` só verifica o volume mínimo.
- Se os HTMLs do Evidently contêm apenas agregados.
- Plano LGPD, base legal, retenção e análise causal no README.
- Roteiro do vídeo.

## Veredito

- **Conformidade:** não atestável. A Etapa 3 (logs, alertas, MLflow, relatório HTML) está estruturalmente atendida no código mostrado. As Etapas 1, 2 e 4 e o roteiro dependem de arquivos ausentes, e não há prova de execução.
- **Qualidade:** engenharia acima da média para o contexto (falhas explícitas, sanitização de mensagens, hashes, invariantes do contrafactual). Ainda não é confiável como evidência, por causa dos itens 1 a 5 e da ausência de teste do caminho de sucesso.
- **Antes da entrega:** corrigir os itens 1 a 4, organizar o histórico de commits e reenviar o pacote com os módulos faltantes e a saída real de `pytest` e de uma execução completa.
