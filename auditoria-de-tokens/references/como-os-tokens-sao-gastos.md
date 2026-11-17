# Como os tokens são gastos

Use este arquivo para explicar o porquê de um achado. Fatos conferidos na documentação oficial em 17/11/2026; as páginas estão no fim.

## A ideia central

O modelo não tem memória entre uma chamada e outra. A cada mensagem, ele recebe **tudo de novo**: as instruções do aplicativo, a lista de ferramentas, skills e conectores, os arquivos de memória, o histórico inteiro da conversa, os arquivos e saídas de ferramentas que já apareceram, e por último a mensagem nova.

Por isso a mensagem 30 de uma conversa custa muito mais que a mensagem 1, mesmo quando a pergunta tem o mesmo tamanho. E no Claude Code um pedido só costuma virar várias chamadas (uma para cada ferramenta usada), cada uma relendo tudo.

## Os quatro fatores

1. **Tamanho do contexto vezes o número de chamadas.** É o fator que mais pesa para a maioria. Conversa longa, anexos grandes, saídas extensas de ferramentas e carga inicial alta entram aqui.
2. **Modelo.** Pela tabela pública da API, o Opus custa o dobro do Sonnet, o Fable custa o dobro do Opus em entrada e saída, e o Haiku custa cerca de um quadragésimo do Opus. No Claude Code, o padrão dos planos pagos é o Opus.
3. **Saída e raciocínio.** O que o modelo escreve custa cinco vezes o que ele lê pela primeira vez, e o raciocínio (thinking) é cobrado como saída. O nível de esforço (effort) controla quanto raciocínio é gerado.
4. **Regravações de cache.** Explicado abaixo.

## Cache: por que reler é barato, e quando deixa de ser

O que se repete de uma chamada para a outra fica em cache, e a releitura do cache custa 5% de uma leitura normal no Opus e no Sonnet, e 10% no Haiku. É por isso que conversas longas ainda são viáveis.

O cache deixa de valer em algumas situações, e aí o contexto inteiro é gravado de novo, a um preço maior que o da leitura normal:

- **Pausa longa.** No Claude Code, dentro do uso do plano, o cache da conversa principal dura uma hora. Subagentes, e a conversa principal quando o plano já estourou, ficam com cinco minutos.
- **Troca de modelo.** Cada modelo tem o seu cache. Trocar no meio regrava tudo. O `opusplan` troca de modelo a cada entrada e saída do modo de planejamento.
- **Mudança de configuração no meio da sessão:** mudar o effort em alguns modelos, conectar ou remover um servidor MCP, ligar ou desligar um plugin, compactar a conversa, atualizar o Claude Code.

Editar o CLAUDE.md no meio da sessão não invalida o cache, porque o arquivo é lido no início.

## O que conta no limite do plano

- Os planos pagos têm um limite por janela de cinco horas e um limite semanal. Os dois aparecem em Configurações > Uso.
- O limite é compartilhado entre o chat, o Claude Code e o app desktop.
- A página de preços diz que a rapidez com que o limite chega depende do modelo, do tamanho das conversas e do tamanho dos arquivos.
- A fórmula exata não é pública. Por isso os scripts desta skill falam em "parte do custo", calculada com os preços públicos da API, e não em porcentagem do limite.
- No plano Pro, os modelos Fable não fazem parte do limite: rodam com créditos de uso, cobrados à parte pelo preço da API. A oferta de lançamento do Fable 5.2 terminou em 16/11/2026.

## Tabela de preços usada (API, 17/11/2026, US$ por milhão de tokens)

| Modelo | Entrada | Saída | Leitura de cache |
|---|---|---|---|
| Haiku 5.5 | 0,10 | 0,50 | 0,01 |
| Sonnet 5.5 | 2 | 10 | 0,10 |
| Opus 5.5 | 4 | 20 | 0,20 |
| Fable 5.2 | 8 | 40 | 0,20 |

Gravar em cache custa 1,25 vez a entrada (cache de cinco minutos) ou 2 vezes (cache de uma hora). O Haiku tem preço maior para pedidos acima de 100 mil tokens. Os valores foram conferidos contra a estimativa de custo que o próprio Claude Code grava nas sessões. Se a tabela mudar, atualize `PRECOS` no início de `scripts/auditar_claude_code.py`.

## O que o Claude Code já faz sozinho

- Guarda o contexto repetido em cache.
- Adia a carga das definições de ferramentas MCP: no início entram só os nomes e as instruções de cada servidor.
- Carrega das skills só o nome e a descrição; o conteúdo entra quando a skill é usada.
- Compacta a conversa quando ela chega ao limite da janela de contexto. Em modelos com janela de um milhão de tokens, isso só acontece perto de 967 mil.
- Mostra o consumo em `/usage` e a ocupação do contexto em `/context`.

O que ele não faz sozinho: escolher um modelo mais barato, baixar o effort, limpar a conversa entre tarefas ou desligar o que você não usa.

## Fontes

- Claude Code: https://code.claude.com/docs/en/costs · /model-config · /prompt-caching · /sub-agents · /skills · /mcp · /hooks · /memory
- Limites e planos: https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work
- Boas práticas de uso: https://support.claude.com/en/articles/9797557-usage-limit-best-practices
- Fable nos planos: https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan
- Créditos de uso: https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans
- Preços: https://claude.com/pricing · https://platform.claude.com/docs/en/about-claude/pricing
