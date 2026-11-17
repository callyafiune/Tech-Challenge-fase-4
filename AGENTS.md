# Instruções de desenvolvimento

- Documentação, comentários, mensagens de log e commits em português do Brasil.
- Preferir Serena para navegação semântica quando o servidor estiver disponível.
- Executar `uv run ruff check .`, `uv run ruff format --check .` e `uv run pytest`.
- Nunca registrar linhas de clientes, identificadores ou valores inválidos nos logs.
- Não confundir mudança nas entradas com comprovação de mudança em P(y|X).
- Cada bloco passa por revisão adversarial no Claude Code com `--model fable`.
- Effort dos agentes Codex: arquitetura e auditoria xhigh; pipelines/modelo e
  estatística high; testes e refatorações simples medium; depuração difícil xhigh.
- Velocidade standard. A apresentação STAR é referenciada pelo vídeo publicado: https://youtu.be/0NyRf1oxfeI.
