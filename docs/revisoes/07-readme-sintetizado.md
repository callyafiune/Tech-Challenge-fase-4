# Revisão adversarial pendente — README sintetizado

Modelo solicitado: `fable`. Nenhum modelo retornou um parecer.

A tentativa foi bloqueada pelo limite de uso de cinco horas do Claude Code. O serviço informou liberação às 20h10 no fuso `America/Sao_Paulo`, em 16/11/2026.

Esta tentativa não constitui revisão aprovada. Os arquivos submetidos, seus hashes e o estado de erro estão no [registro da tentativa](07-readme-sintetizado.json). A alteração é documental; o pipeline não foi modificado.

Para repetir a revisão após a liberação:

```powershell
uv run python -X utf8 scripts/revisar_bloco.py 07-readme-sintetizado README.md docs/governanca.md docs/operacao.md docs/resultados.md --foco "Revisar sintese, tabelas, links e preservacao dos detalhes de governanca e operacao. Alteracao exclusivamente documental."
```
