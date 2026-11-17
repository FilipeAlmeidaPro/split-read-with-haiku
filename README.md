# Split Read with Haiku

Divide o trabalho no Claude Code: o Haiku procura e lê, e o modelo da sua conversa pensa, decide e edita. Para quem usa o Claude no plano Pro e quer que o limite renda mais. O kit tem três peças e um guia.

| Peça | Onde funciona | O que faz |
|---|---|---|
| Ajudante no Haiku | Claude Code | O trabalho de procurar e ler passa a ser feito pelo Haiku, que custa cerca de 40 vezes menos que o Opus. O modelo da sua conversa continua pensando, decidindo e editando. |
| Aviso ao fim da resposta | Claude Code | Mostra quanto foi lido pelo Haiku, qual foi o ganho e quanto ficou com o modelo da conversa. |
| Auditoria de tokens | Claude Code e chat | Mede para onde os seus tokens foram e indica as três mudanças de maior impacto. |
| Guia de duas páginas | Qualquer lugar | Explica por que o limite acaba e o que fazer, no chat e no Claude Code. |

Para entender o que o Claude já faz sozinho e o que cada peça muda, leia [VISAO-GERAL.md](VISAO-GERAL.md).

## No Claude Code

### Instalar

```bash
bash instalar.sh
```

No Windows: `python ajudante-haiku\configurar.py instalar`.

A instalação mexe em cinco lugares, e em nenhum outro:

| Lugar | O que entra |
|---|---|
| `~/.claude/skills/auditoria-de-tokens/` | A skill de auditoria (pasta nova). |
| `~/.claude/agents/ajudante-haiku.md` | O ajudante (arquivo novo). |
| `~/.claude/split-read-with-haiku/` | Os programas do kit e as cópias de segurança (pasta nova). |
| `~/.claude/CLAUDE.md` | Um bloco marcado no fim do arquivo, com as regras de quando delegar. |
| `~/.claude/settings.json` | Um hook `Stop`, que imprime o aviso ao fim de cada resposta. |

Antes de alterar o `CLAUDE.md` e o `settings.json`, o instalador guarda uma cópia. **O modelo da sua conversa não é alterado.**

Opções:

- `bash instalar.sh --sem-resumo`: sem o aviso com números. Não toca no `settings.json`.
- `bash instalar.sh --so-auditoria`: só a skill de auditoria.

### O que você passa a ver

Quando o Claude delega uma busca, o nome `ajudante-haiku` aparece na tela. No fim da resposta ele escreve:

> Observação: a leitura foi feita pelo ajudante no Haiku; a análise e as edições ficaram com o modelo da conversa.

Em seguida vem o aviso com os números medidos, neste formato:

> Observação (Split Read with Haiku): neste pedido, a leitura foi feita pelo ajudante no Haiku (9 chamadas, 212 mil tokens, cerca de US$ 0,03). Nos preços do Opus, os mesmos tokens custariam cerca de US$ 0,61: ganho de cerca de 95%. O Opus fez o restante: 480 mil tokens lidos e 3,1 mil escritos, cerca de US$ 0,19. Valores em preço de API, só para comparar.

Os números desse exemplo são ilustrativos. O aviso só aparece quando algo foi delegado.

### O que o ajudante pode fazer

- Ele tem três ferramentas: ler arquivo, buscar texto e buscar arquivo por nome.
- Ele não tem terminal nem ferramentas de edição. Não consegue alterar, criar ou apagar nada.
- Ele só é chamado para buscas de três ou mais passos. Para um ou dois passos, delegar custaria mais do que resolver.
- O modelo da conversa confere o trecho que importa antes de decidir ou editar.

### Desligar ou remover

- Na conversa, diga **"sem ajudante"** para desligar a delegação naquela sessão.
- Para remover o ajudante, a nota e o aviso:

```bash
bash ~/.claude/split-read-with-haiku/desinstalar.sh
```

- Com `--tudo`, a skill de auditoria sai junto.
- O aviso lembra desse comando na primeira vez e depois a cada dez avisos.

### Auditoria

Em uma sessão nova, peça: **"audite meus tokens"**. Uma auditoria acrescenta cerca de 6 mil tokens à conversa, porque quem lê os registros é um programa no seu computador.

Para saber quanto o ajudante economizou na sessão:

```bash
python3 ~/.claude/split-read-with-haiku/resumo_do_pedido.py --sessao
```

## No chat

O ajudante e o aviso não existem no chat, porque lá não há ajudantes para configurar. O que funciona é a auditoria e o guia.

1. Em Configurações > Recursos, ative a execução de código, se ainda não estiver ativa.
2. Em Personalizar > Skills, clique em "+" > Criar skill > Enviar uma skill e escolha o arquivo `auditoria-de-tokens.zip`.
3. Em uma conversa nova, peça: **"audite meu uso do Claude"**.

A skill analisa o histórico exportado do chat, estima o peso de arquivos antes de anexar e, sem a exportação, faz uma entrevista de seis perguntas. Os nomes dos menus podem mudar; procure por "Skills" nas configurações.

## Em outras ferramentas

O ajudante é um recurso do Claude Code. Ele não se aplica ao Codex nem a outros assistentes de código.

## Privacidade

- Os programas só leem. Nada é alterado fora dos cinco lugares listados acima.
- Nenhum programa acessa a rede.
- Eles medem tamanhos e contagens. Não leem nem imprimem o texto das suas conversas.
- O relatório da auditoria mostra nomes de pastas de projeto e de servidores MCP. Para compartilhar, use `--anonimo`.

## Requisitos

Python 3.8 ou mais novo, sem bibliotecas extras. Claude Code 2.1.208 ou mais novo para o ajudante.

## Limites

- A Anthropic não publica a fórmula do limite dos planos. Os valores em dólar usam os preços públicos da API (17/11/2026) para comparar. Não são a conta do plano.
- O ajudante pode deixar passar algo numa busca. Por isso o modelo da conversa confere o que importa.
- O Claude decide quando delegar com base em uma instrução. Ele segue na maioria das vezes, não em todas.
- O aviso com números lê o registro da sessão, que é gravado com um pequeno atraso. A última resposta pode ficar de fora da conta.
- O ganho mostrado no aviso compara os mesmos tokens em dois preços. Ele não simula como o modelo da conversa teria feito a busca sozinho.
- O Claude Code apaga registros de sessão antigos (30 dias por padrão), então a auditoria cobre no máximo esse período.
- A exportação do chat não informa modelo, raciocínio, ferramentas nem imagens. O resultado é um piso.
- Comandos, menus e preços foram conferidos na documentação oficial em 17/11/2026 e podem mudar.

O que já foi testado e o que ainda não foi está no fim de [VISAO-GERAL.md](VISAO-GERAL.md).

## Fontes

- Claude Code: https://code.claude.com/docs/en/costs, /sub-agents, /hooks, /model-config, /prompt-caching, /skills, /memory
- Limites: https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work
- Boas práticas: https://support.claude.com/en/articles/9797557-usage-limit-best-practices
- Fable nos planos: https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan
- Skills no chat: https://support.claude.com/en/articles/12512180-use-skills-in-claude
- Preços: https://platform.claude.com/docs/en/about-claude/pricing

## Licença

MIT. Veja o arquivo [LICENSE](LICENSE).

Material independente, sem vínculo com a Anthropic.
