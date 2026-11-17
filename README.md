# Kit de economia de tokens para o Claude

Para quem usa o Claude no plano Pro e quer que o limite renda mais. O kit tem duas partes:

- **`auditoria-de-tokens/`**: uma skill que mede para onde os seus tokens estão indo e monta um plano com as três mudanças de maior impacto. Funciona no Claude Code e no chat.
- **`guia/`**: um guia de duas páginas para imprimir ou compartilhar.

A skill não é uma lista de dicas. Ela lê os seus dados, mostra o número por trás de cada recomendação e diz também o que não é problema no seu caso.

Para entender o que o Claude já faz sozinho, o que a skill é e o que ela não é, leia [VISAO-GERAL.md](VISAO-GERAL.md).

## O que ela mede

**No Claude Code** (terminal, aba Code do app, extensões de IDE), o script `auditar_claude_code.py` lê as configurações e os registros de sessão da pasta `~/.claude` e responde:

- Quanto foi gasto por modelo, e quanto isso custaria em preço de API.
- Que parte do gasto veio de conversas longas, de subagentes, de raciocínio e de regravações de cache.
- Quanto pesa a carga inicial de cada sessão, e que parte dela você controla.
- Quais hooks, skills, plugins e servidores MCP entram em toda sessão.
- Quais ferramentas mais trouxeram texto e quais sessões foram as mais caras.

**No chat** (claude.ai, app desktop e celular):

- `analisar_export_chat.py` lê a exportação do seu histórico e mostra quais conversas mais pesaram, quanto veio de conversas longas e de anexos, e quanto você economizaria abrindo conversas novas.
- `estimar_arquivo.py` estima quanto um PDF, planilha, documento ou imagem pesa antes de você anexar.
- Sem exportação, a skill faz uma entrevista de seis perguntas.

## Instalação

### Claude Code

Copie a pasta `auditoria-de-tokens` para `~/.claude/skills/`. No macOS e no Linux:

```bash
bash instalar.sh
```

No Windows, copie a pasta para `%USERPROFILE%\.claude\skills\`.

Abra uma sessão nova e peça: **"audite meus tokens"**.

### Chat

1. Em Configurações > Recursos, ative a execução de código, se ainda não estiver ativa.
2. Em Personalizar > Skills, clique em "+" > Criar skill > Enviar uma skill e escolha o arquivo `auditoria-de-tokens.zip`.
3. Em uma conversa nova, peça: **"audite meu uso do Claude"**.

Os nomes dos menus podem mudar; procure por "Skills" nas configurações.

## Privacidade

- Os scripts só leem. Nada é alterado sem você confirmar, e a skill faz backup antes de qualquer edição.
- Nenhum script acessa a rede.
- Os scripts medem tamanhos e contagens. Eles não leem nem imprimem o texto das suas conversas.
- O relatório mostra nomes de pastas de projeto e de servidores MCP. Para compartilhar, use `--anonimo`.

## Requisitos

Python 3.8 ou mais novo, sem bibliotecas extras. Para PDFs, o estimador fica mais preciso com `pypdf` instalado. Sem Python, a skill faz uma medição manual mais simples.

## Limites

- A Anthropic não publica a fórmula do limite dos planos. As porcentagens do relatório usam os preços públicos da API (17/11/2026) para comparar causas entre si. Não são a conta do plano.
- O Claude Code apaga registros de sessão antigos (30 dias por padrão), então a auditoria cobre no máximo esse período.
- A exportação do chat não informa modelo, raciocínio, ferramentas nem imagens. O resultado é um piso.
- Comandos e menus foram conferidos na documentação oficial em 17/11/2026 e podem mudar.

## Fontes

- Claude Code: https://code.claude.com/docs/en/costs, /model-config, /prompt-caching, /sub-agents, /skills, /mcp, /hooks, /memory
- Limites: https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work
- Boas práticas: https://support.claude.com/en/articles/9797557-usage-limit-best-practices
- Fable nos planos: https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan
- Skills no chat: https://support.claude.com/en/articles/12512180-use-skills-in-claude
- Preços: https://platform.claude.com/docs/en/about-claude/pricing

Material independente, sem vínculo com a Anthropic.
