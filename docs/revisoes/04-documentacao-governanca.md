# Revisão adversarial — 04-documentacao-governanca

Ferramenta de revisão: Claude Code, modelo `claude-fable-5-2`.

# Parecer adversarial: documentação, governança, roteiro e rastreabilidade

**Escopo.** Parecer estático, sem execução. Recalculei os números do `resumo.json` e os comparei com README, model card, resultados e matriz. Não recebi `index.html`, `manifesto.json`, `logs.jsonl`, `alertas.json`, `monitoring.json`, `evidently.*`, `auditoria_final.md`, `progresso.md`, `params.yaml`, os testes nem o CI. Não recalculei os hashes de `publicacao.json` nem acessei os links externos.

**Coerência numérica: sem defeitos.** Todos os números de `resultados.md`, README e model card batem com o `resumo.json`:
- **Contagens:** 22 eventos, 8 alertas, duração de 26,905 s, partições e taxas de classe (3318 + 995 + 996 + 1327 = 6636).
- **Métricas:** as matrizes de confusão reproduzem F1, recall, precisão, acurácia e taxas de predição positiva.
- **Estatística:** o ajuste BH das 14 contínuas está correto nos dois cenários; deltas dos alertas, pares de Brier e intervalos conferem.
- **Inversões:** as contagens de rótulos invertidos fecham com as prevalências (conceito 1342 − 202; combinado 942 − 172).

## Críticos

**C1. `docs/resultados.md` chegou com codificação corrompida.** Acentos, travessões e separadores viraram `?` ("execu??o", "T0?T3"), e faltam espaços antes de números ("Treino15000", "de500"). A falta de espaços também aparece em `matriz_rastreabilidade.md` e `tratamento.md` ("real30.000", "fixo0,30", "até5min").
- **Impacto:** se o defeito estiver em disco, o documento central de evidência fica ilegível. Se ocorrer só no empacotamento de `scripts/revisar_bloco.py`, o conteúdo revisado difere dos bytes cujo SHA-256 o JSON da revisão registra.
- **Correção:** conferir os bytes em disco. Gerar `resultados.md` a partir do `resumo.json` com script versionado em UTF-8 (hoje não há gerador entre os fontes com hash). Padronizar o formato numérico pt-BR ("30,000" e "26.91" estão em formato inglês).

## Importantes

**I1. A evidência do contrato não mostra qual regra disparou.** Em `resumo.json → contracts.rules` há apenas `blocked: true` e `rejected_rows: 10`, que é o tamanho do lote, não o número de linhas violadoras. As durações são suspeitas: nulo 0,00016 s e combinado 0,00021 s, contra cerca de 0,0175 s para idade e duplicidade.
- **Impacto:** os tempos sugerem que o nulo é barrado por pré-checagem fora do Pandera e que o lote combinado para no primeiro erro. Não fica demonstrado que as três regras passam pelo Pandera (critério de 25%).
- **Correção:** registrar por caso o nome do check e a coluna que falharam e a contagem de linhas violadoras, sem valores. Usar `lazy=True` no lote combinado.
- **Relacionado:** `inference_calls: 0` é uma constante, não uma medição. Instrumentar ou remover o campo.

**I2. A regra de conceito pareado não gera alerta para o par combinado.** `concept_combined` satisfaz a regra do README (aumento de 0,228, IC inferior de 0,211), mas só existe `CONCEITO_SIMULADO` para `concept`.
- **Correção:** emitir o alerta para o par combinado ou restringir a regra documentada.
- **Relacionado:** `prediction_monitoring.score.drift: true` no covariável (taxa de predição positiva de 21,1% para 38,9%) não gera alerta nem aparece na tabela de regras.

**I3. A segunda variável com drift está dentro do ruído amostral.** O PSI de `pay_0` é 0,2053 contra limiar de 0,20, sem intervalo. A frase "pesos e limiares não foram alterados" não é comprovável sem histórico de commits.
- **Correção:** publicar um IC bootstrap do PSI e declarar a fragilidade em `resultados.md`, sem ajustar pesos depois do fato.

**I4. O Evidently covariável provavelmente contradiz a fala do roteiro.** As 14 contínuas têm p bruto ≤ 0,022 nesse cenário. Se o Evidently usa KS bruto a 5%, deve marcar cerca de 15 de 20 colunas, não as "duas variáveis" da matriz (R05) e do roteiro (1:50). É inferência: o `evidently.json` não veio no pacote.
- **Correção:** registrar em `resultados.md` a contagem real do Evidently e ajustar a fala.

**I5. `docs/verificacao.json` não está vinculado ao código executado.** O instante 21:15:56 cai dentro da janela do pipeline (21:15:36 a 21:16:03), e o pytest sozinho dura 71 s. Ou as execuções foram concorrentes, o que contamina duração, RSS e CPU, ou o carimbo não foi medido. As saídas são paráfrases, e o arquivo não traz `source_sha256`.
- **Correção:** gerar por script, com início e fim, stdout literal e hash das fontes, em sequência após a execução final.

**I6. A cobertura de hashes das fontes é incompleta.** O Ruff relata 40 arquivos; `source.files_sha256` cobre 23 arquivos `.py`. Ficam de fora cerca de 17, possivelmente `conftest.py` e fixtures.
- **Impacto:** com árvore suja e sem commits, esse inventário é a única identidade do código. A frase da matriz "código identificado por hashes" está exagerada.
- **Correção:** incluir todos os `.py`, o workflow do CI e `.python-version`.

**I7. A causalidade não está no README.** O enunciado pede "Governança e Causalidade no README" e uma "análise causal do problema". O README só tem o link para `docs/causalidade.md`, e a matriz não tem linha para isso.
- **Correção:** criar seção própria com o mecanismo e a decomposição que os dados já permitem: degradação total do combinado contra a referência de 0,2499, sendo 0,0218 de composição e 0,2281 da intervenção no alvo.
- **Também falta dizer:** no covariável a AUROC subiu (0,7965) e não houve alerta supervisionado. Toda a degradação vem da inversão sintética, que leva a prevalência a 67% e a AUROC abaixo de 0,5, sem plausibilidade econômica.

**I8. Vieses são auditados, mas não mitigados nem reportados.** O critério fala em "mitigação de vieses". Os achados não aparecem no README nem em `resultados.md`: a faixa de 50 anos ou mais tem FPR de 0,159 contra 0,114, AUROC de 0,748 e diferença de 5,9 p.p. na taxa de aprovação.
- **Lacunas:** idade segue como preditor sem ablação nem critério de ação. A auditoria só cobre a referência, não os cenários.
- **Incoerência:** o artefato publica `approval_rate`, enquanto o README afirma que não há decisão de concessão.

**I9. O plano de LGPD omite as normas setoriais que regem score de crédito.**
- **Normas ausentes:** Lei 12.414/2011 (Cadastro Positivo), Súmula 550 do STJ, art. 43, §1º do CDC (prazo de cinco anos, relevante para retenção) e o RIPD do art. 38.
- **Classificação das colunas:** falta dizer que nenhuma é dado sensível no sentido do art. 5º, II, embora sexo e idade sejam atributos de risco discriminatório.
- **Redação:** "art. 7º, X não autoriza uso indiscriminado" é fraco; o art. 11 simplesmente não prevê a hipótese de proteção do crédito.

**I10. O roteiro tem quatro problemas.**
- **Números ausentes:** a fala remete a `resultados.md` em vez de citar os valores. Sugestões: AUROC de 0,783 para 0,407; recall de 0,54 para 0,19; Brier +0,347 com IC [0,327; 0,368]; 8 alertas.
- **Mapeamento STAR cruzado:** o plano de governança deveria estar em Action e os alertas em Result. O impacto não é quantificado.
- **Tempo sem folga:** os blocos somam exatamente 300 s, com cerca de oito trocas de tela.
- **Execuções diferentes na tela:** os comandos rodam um pipeline novo, mas servem o snapshot antigo. O HTML e o MLflow mostrarão IDs distintos; o run `99897dc9…` não existirá em outro clone.

**I11. O rastreamento "pai e quatro filhos" não tem evidência no repositório.** `resumo.json → tracking` traz só o run pai.
- **Correção:** registrar os IDs dos filhos e exportar os metadados agregados dos runs.

**I12. A alegação de privacidade do snapshot não é verificada pelo código.** `scripts/exportar_evidencias.py` copia uma lista fixa de arquivos e declara as exclusões como literal, sem inspecionar o conteúdo.
- **Lacunas:** não confere os hashes contra o manifesto de origem, e uma falha no meio da cópia deixa o destino parcial. Publica `output_dir` e a URI com o caminho absoluto `C:\estudos\…`, apesar da sanitização alegada no tratamento.
- **Política inconsistente:** a supressão de grupos com menos de 30 registros vale só para a auditoria de equidade; os histogramas do Evidently expõem categorias raras de `pay_*`.

## Menores

- **M1.** "Os parâmetros efetivos estão em `params.yaml`" não vale para o limite de disco de 1 GiB, as frações do split, as seeds derivadas (43, 44, 46), o mínimo de 30 e os limites do contrato.
- **M2.** A tabela do README diz "PSI ≥ 0,20 ou KS…", mas a regra é por tipo de variável: PSI só nas discretas, KS só nas contínuas.
- **M3.** O esquema do `resumo.json` tem três rótulos enganosos:
  - `concept_combined.control_*` contém valores do covariável;
  - `concept_status: "requires_pair"` aparece mesmo nos cenários já pareados;
  - `counterfactual: true` aparece no controle, que usa rótulos originais.
- **M4.** Quatro expressões exageram:
  - "registros históricos imutáveis": são arquivos não versionados;
  - "revisão independente": é revisão estática por modelo;
  - "execução validada": não houve inspeção visual;
  - "evidências já incluídas no repositório": `reports/` não está versionado.
- **M5.** "Alertas não enviados a terceiros" e "o script envia código e documentação" não se sustentam: esta rodada enviou alertas, caminhos locais e IDs de execução.
- **M6.** A referência de drift é um holdout, não o conjunto de treino, como diz o enunciado ("Referência (usado no treino)"). É defensável, mas precisa de justificativa explícita.
- **M7.** Comparar AUROC com um dummy de prior (0,50) é trivial. Informar também o ganho de Brier: 0,138 contra 0,172.
- **M8.** Quatro pontos de redação jurídica:
  - "bloqueio de finalidade" não é termo da LGPD;
  - o canal de direitos é obrigação do controlador, não do encarregado;
  - falta citar a Resolução CD/ANPD nº 15/2024;
  - o link de `normas.leg.br` está rotulado como "Senado".
- **M9.** `.env.example` não está documentado, embora o README diga que não há chave de API.

## Pendências declaradas (não contadas como alegação de atendimento)

- **Histórico de commits:** hoje há um único commit, "Initial commit", que não é semântico. Vários arquivos estão em estado `AM`, ou seja, o índice guarda versões defasadas; é preciso reestagiar antes de commitar.
- **Demais:** vídeo e link, CI remoto e inspeção visual dos HTMLs.

## Veredito

**Conformidade: parcial.** As etapas 1 a 3 têm números íntegros e internamente coerentes. Ficam abertos:
- o vínculo entre o histórico semântico e as fontes executadas;
- a causalidade no README (I7);
- a evidência por regra do contrato (I1);
- a mitigação de vieses (I8).

**Qualidade: boa, mas não pronta para entrega.** As limitações são declaradas com honestidade e não encontrei números inflados. Antes de entregar, é preciso resolver C1 e os itens I1, I2, I5, I6 e I10, além de uma inspeção humana dos HTMLs.
