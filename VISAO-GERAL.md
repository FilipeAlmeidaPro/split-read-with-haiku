# Visão geral: o que é o quê

Este arquivo separa quatro coisas: o que o Claude já faz sozinho, o que cada peça do kit é, o que muda no Claude de quem instala e o que o kit não é.

## 1. O que o Claude já tem, sem instalar nada

| O quê | Onde | O que mostra ou faz | O que falta |
|---|---|---|---|
| `/usage` | Claude Code | Consumo da sessão e limites do plano. Segundo a documentação, também divide o consumo por skills, subagentes, plugins e servidores MCP. | Não olha o histórico de várias sessões nem aponta a causa. |
| `/context` | Claude Code | O que ocupa o contexto da sessão aberta. | Só a sessão atual. |
| Configurações > Uso | Chat e app | Quanto resta da janela de cinco horas e do limite semanal. | Não diz o que gastou. |
| Skill embutida `explain-usage` | App desktop, em algumas instalações | Um gráfico de para onde foram os tokens da sessão atual. | Uma sessão só, sem correção, com pesos aproximados. |
| Ajudantes (subagentes) | Claude Code | O Claude já abre ajudantes para buscas e tarefas paralelas. | Por padrão eles rodam no mesmo modelo da conversa, ou seja, no mais caro. |
| Controles: `/model`, `/effort`, `/clear`, `/compact` | Claude Code | São os botões que reduzem o gasto. | O Claude não aperta nenhum deles sozinho. |

Resumo: o Claude já mede a sessão atual, já tem ajudantes e já tem todos os botões. Ele não manda o trabalho braçal para o modelo barato e não diz qual botão apertar no seu caso.

## 2. As três peças do kit

### Ajudante no Haiku (faz)

- **O que é:** um arquivo de agente, `ajudante-haiku.md`, mais um bloco de regras no `CLAUDE.md`.
- **O que faz:** quando uma busca pede três ou mais passos, o Claude chama esse ajudante, que roda no Haiku. O Haiku custa cerca de 40 vezes menos que o Opus.
- **Onde:** só no Claude Code.

### Aviso ao fim da resposta (mostra)

- **O que é:** um programa pequeno, `resumo_do_pedido.py`, ligado a um hook `Stop`.
- **O que faz:** depois de cada resposta em que houve delegação, imprime quanto foi lido pelo Haiku, o ganho e quanto ficou com o modelo da conversa. Não gasta tokens do modelo.
- **Onde:** só no Claude Code.

### Auditoria de tokens (indica)

- **O que é:** uma skill com três programas que só leem.
- **O que faz:** olha até 30 dias de uso, ordena as causas por custo e entrega as três mudanças de maior impacto, com o número de cada uma e com o que não é problema no caso da pessoa.
- **Onde:** no Claude Code e no chat. No chat, ela lê o histórico exportado.

## 3. O que muda no Claude de quem instala

| | Muda? | Detalhe |
|---|---|---|
| O modelo da conversa | Não | Quem pensa, responde, decide e edita continua sendo o modelo que a pessoa escolheu. |
| Quem procura e lê | Sim | Buscas de três ou mais passos vão para o ajudante no Haiku. |
| O que o ajudante consegue fazer | Só ler | Ele tem três ferramentas: ler arquivo, buscar texto e buscar arquivo por nome. Sem terminal e sem edição. |
| O que aparece na tela | Sim | O nome `ajudante-haiku` em cada delegação, uma linha de observação no fim da resposta e o aviso com números. |
| Arquivos de configuração | Dois | Um bloco marcado no `CLAUDE.md` e um hook no `settings.json`, os dois com cópia de segurança. |

Para desligar em uma sessão, a pessoa diz "sem ajudante". Para remover tudo, roda `bash ~/.claude/kit-economia-de-tokens/desinstalar.sh`. O aviso lembra desse comando na primeira vez e depois a cada dez avisos.

## 4. O que o kit não é

- **Não troca o modelo da conversa.** Nem escondido, nem no meio da tarefa.
- **Não usa o Sonnet de forma automática.** O Sonnet custa metade do Opus, e delegar edição a um modelo menor é um risco que o kit evita. Ele continua como escolha manual da pessoa, com `/model sonnet`.
- **Não substitui os ajudantes embutidos do Claude.** Trocar o modelo deles funcionaria, mas o nome na tela continuaria o mesmo e a pessoa não veria a mudança.
- **Não garante que toda busca será delegada.** A regra é uma instrução para o modelo, que a segue na maioria das vezes.
- **Não calcula o limite do plano.** A fórmula não é pública. Os valores usam os preços públicos da API para comparar.
- **Não lê o texto das conversas.** Só tamanhos, contagens e nomes de modelos, ferramentas e pastas.
- **Não funciona no chat nem no Codex,** no caso do ajudante e do aviso. No chat valem a auditoria e o guia.

## 5. Por que vale ter

- **O trabalho braçal sai do modelo caro.** Cada passo de busca feito pelo Opus relê a conversa inteira no preço do Opus. O ajudante faz os mesmos passos com um contexto pequeno, no preço do Haiku.
- **A conversa principal cresce menos.** O ajudante lê os arquivos e devolve só os achados.
- **A pessoa vê o que aconteceu.** Nome na tela, observação e números ao fim de cada resposta.
- **A auditoria prova ou desmente.** Ela mostra quanto do custo estava em cada modelo antes e depois, e aponta as outras causas, como conversa longa.

## 6. Qual modelo para quê

| Modelo | Quando | Custo em relação ao Opus |
|---|---|---|
| Haiku | Trabalho mecânico: procurar, ler, listar. É o que o ajudante faz. | Cerca de 40 vezes menor |
| Sonnet | Sessões do dia a dia, por escolha da pessoa | Metade |
| Opus | Raciocínio, decisão e edição | Referência |
| Fable | No plano Pro, só com créditos de uso, cobrados à parte | O dobro |

## 7. Estado atual

Testado:

- **Auditoria:** em uma máquina, com dados reais.
- **Instalação e remoção:** em uma pasta de teste com arquivos já existentes e em uma instalação real. Reinstalar não duplica nada, e remover devolve o `CLAUDE.md` e o `settings.json` ao conteúdo original.
- **O ajudante instalado:** em uma sessão real, ele rodou no Haiku, usou só busca e leitura, acertou três buscas e respondeu "não encontrei" na que não existia. Quando recebeu o pedido de criar um arquivo, não conseguiu, porque não tem ferramenta de escrita nem de terminal.
- **Aviso com números:** o hook rodou sem erro em uma sessão real, e o texto apareceu na tela ao fim da resposta, no app desktop.

Ainda não testado:

- **Delegação espontânea.** Falta ver, em uma sessão nova, o Claude chamando o ajudante por causa da nota do `CLAUDE.md`, sem ninguém pedir.
- **O aviso no terminal e nas extensões de IDE.** Só foi visto no app desktop.
- **O leitor do histórico do chat com uma exportação real,** os caminhos de menu do chat e o Windows.
