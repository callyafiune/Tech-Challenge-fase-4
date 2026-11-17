# Plano — execução enxuta com Docker

**Objetivo:** executar o fluxo exigido pelo enunciado com um comando, levando apenas código, configuração e dependências de execução para a imagem.

**Escopo:** o enunciado não exige API HTTP, contêiner ou serviço contínuo. A execução padrão deve validar dados, treinar o modelo, simular cenários, produzir HTML e rastrear resultados no MLflow SQLite; ao concluir, deve encerrar com o código de saída da CLI.

**Decisão de arquitetura:** Python 3.11 slim, instalação congelada em estágio intermediário com uv 0.11.6, ambiente virtual copiado para o estágio final, usuário sem privilégios e volumes separados para cache e resultados. A imagem não inclui uv, testes, ferramentas de desenvolvimento, relatórios históricos, dados ou modelos do host. As dependências transitivas declaradas pelas bibliotecas são preservadas.

**Alternativas consideradas:** somente inferência não demonstra as etapas obrigatórias do desafio; uma API adicionaria um contrato HTTP ao fluxo executado em lote. Alpine exigiria verificar disponibilidade das rodas científicas para musl e potencialmente compilar dependências; a variante slim permite usar as distribuições binárias existentes.

## Bloco de implementação e aceite

- [x] Criar `Dockerfile` com instalação em múltiplos estágios e `.dockerignore` com lista explícita do conteúdo permitido.
- [x] Criar `compose.yaml` com um serviço de execução, cache e artefatos persistidos em volumes, sem portas publicadas; incluir override `compose.sem-rede.yaml` para a repetição isolada.
- [x] Executar build e verificar ausência de pytest, Ruff, uv e dados do host na imagem final.
- [x] Executar a CLI completa com aquisição real da UCI; conferir contratos, quatro cenários, HTML, alertas e SQLite pai/filhos.
- [x] Repetir a execução com cache e sem rede para verificar reprodutibilidade operacional.
- [x] Medir o tamanho da imagem e documentar comandos de execução, inspeção e limpeza em `docs/docker.md`; resumir o uso no README.
- [x] Versionar `scripts/verificar_docker.py`, com build único, vínculo do ID da imagem, inspeção sem volumes, falha esperada sem cache, exportação com hashes e consulta HTTP da UI.
- [x] Executar Ruff, formatação e pytest; submeter o bloco à revisão adversarial com Claude Code `--model fable` e tratar achados concretos.

Evidências: [verificação Docker](verificacao_docker.json), [guia e resultados](docker.md), [parecer inicial](revisoes/08-docker.md), [fechamento com ressalvas](revisoes/08c-docker-evidencias.md) e [tratamento dos achados](revisoes/08-docker-tratamento.md). A qualidade local tem [coletor independente](../scripts/verificar_qualidade.py) e [registro próprio](validacao/docker-qualidade-final.json).

## Limites de auditoria

A imagem omite testes, scripts e histórico Git: seu manifesto de fontes representa o código efetivamente presente no contêiner e não deve ser apresentado como idêntico ao manifesto da execução histórica no host. O modelo é treinado no Linux durante a execução, evitando depender da portabilidade de um artefato binário produzido no Windows. Não se altera o algoritmo nem a política estatística.
