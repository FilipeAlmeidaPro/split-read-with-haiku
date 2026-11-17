# Correções do Claude Code

Uma seção por achado do relatório. O identificador no título é o mesmo que aparece em "Correção:" no relatório.

Regras para qualquer edição de arquivo:

1. Copie o original antes: `cp ~/.claude/settings.json ~/.claude/settings.json.bak-AAAA-MM-DD`.
2. Mostre à pessoa o trecho que muda e espere a confirmação.
3. Depois de editar, confira que o arquivo ainda é JSON válido.
4. Os nomes de chave abaixo foram conferidos na documentação em 17/11/2026. Se uma chave não se comportar como descrito, consulte a página indicada antes de insistir: a configuração do Claude Code muda entre versões.

Índice: modelo · effort · conversa-longa · cache · carga-fixa · hooks · saidas-grandes · subagentes · skills · claude-md · mcp · chave-api · medição manual

---

## modelo

**Por que pesa.** Pela tabela pública, a mesma sessão custa cerca de metade no Sonnet e cerca de um quadragésimo no Haiku, em comparação com o Opus. O Fable custa o dobro do Opus. O padrão do Claude Code nos planos pagos é o Opus, então quem nunca mexeu nisso roda tudo no modelo mais caro. A documentação afirma que o Sonnet dá conta da maior parte das tarefas de código.

**Como confirmar.** Tabela "Para onde foram os tokens" do relatório; `/model` mostra o modelo atual.

**Correção.**
- `/model sonnet` define o Sonnet como padrão das próximas sessões. No seletor, a tecla `s` aplica só à sessão atual.
- Use o Opus para o que é difícil de verdade: arquitetura, bug sem pista, decisão que custa caro se sair errada. Troque no início da sessão ou logo depois de `/clear`.
- `opusplan` usa o Opus no modo de planejamento e o Sonnet na execução. Cada entrada e saída do modo de planejamento é uma troca de modelo, com regravação do cache; funciona melhor com um plano por sessão do que alternando o tempo todo.
- Haiku serve para sessões simples e repetitivas: renomear, formatar, extrair dados.
- Se o relatório mostrar uso do Fable: no plano Pro ele não entra no limite e roda com créditos de uso, cobrados à parte pelo preço da API. Confirme com a pessoa se os créditos estão ligados em Configurações > Uso e se ela sabe disso.

**O que se perde.** Em problemas difíceis o Sonnet erra mais e pode precisar de mais idas e vindas. Se a pessoa notar retrabalho, o Opus sai mais barato naquela tarefa.

**Como desfazer.** `/model default` volta ao padrão do plano.

Fonte: /model-config, /costs.

---

## effort

**Por que pesa.** O raciocínio é cobrado como saída, que custa cinco vezes a entrada. Effort alto faz o modelo raciocinar muito mesmo em pedidos simples. Nos modelos da família 5.5 e nos Fable não dá para desligar o raciocínio; o que existe é baixar o nível.

**Como confirmar.** O relatório mostra o nível usado nas chamadas e a parcela da saída que foi raciocínio. `/effort status` mostra o nível atual.

**Correção.**
- `/effort medium` é o padrão dos modelos atuais. `/effort low` para trabalho mecânico.
- Para um pedido específico que precisa de raciocínio profundo, escreva `ultrathink` no pedido em vez de subir o nível da sessão.
- O `/effort` grava a preferência por modelo, em `modelSettings`. Uma chave `effortLevel` solta no topo do settings.json do usuário não vale para o Opus 5.5.
- A variável `CLAUDE_CODE_EFFORT_LEVEL` passa por cima de tudo. Se ela aparecer no relatório, é ela que manda.

**O que se perde.** Respostas menos elaboradas em problemas complexos. Compense subindo o nível só naquela sessão.

**Como desfazer.** `/effort auto`, ou escolha outro nível.

Fonte: /model-config.

---

## conversa-longa

**Por que pesa.** Cada chamada relê a conversa inteira. Com 300 mil tokens de contexto, um pedido que usa dez ferramentas relê três milhões de tokens. Em modelos com janela de um milhão, a compactação automática só acontece perto de 967 mil, então a conversa cresce sem aviso.

**Como confirmar.** Achados "Conversas que continuam depois de ficarem grandes" e "Compactação só acontece quando o contexto está no limite"; coluna "Pico de contexto" das sessões mais pesadas; `/context` na sessão aberta.

**Correção.**
- `/clear` ao trocar de tarefa. Não custa nada e a próxima chamada começa só com a carga inicial.
- Antes do `/clear`, quando a tarefa continua depois: peça ao Claude para gravar o estado em um arquivo (objetivo, decisões, o que falta, arquivos envolvidos) e comece a sessão seguinte pedindo para ler esse arquivo.
- `/compact` com instrução do que manter, por exemplo `/compact mantenha as decisões e os nomes dos arquivos alterados`. A compactação é uma chamada grande; faça antes de a conversa ficar enorme.
- `/autocompact <tamanho>` faz a compactação automática acontecer mais cedo. A chave equivalente é `autoCompactWindow`, entre 100 mil e 1 milhão. Para a maioria, 200 mil é um bom teto.
- Uma seção "# Compact instructions" no CLAUDE.md orienta o que preservar em toda compactação.

**O que se perde.** Detalhes antigos da conversa. O arquivo de estado resolve o que importa.

**Como desfazer.** `/autocompact` com o valor anterior. `/clear` não tem desfazer, mas a sessão antiga continua disponível em `/resume`.

Fonte: /costs, /model-config, /how-claude-code-works.

---

## cache

**Por que pesa.** Quando o cache expira ou é invalidado, o contexto inteiro é gravado de novo, a um preço maior que o de uma leitura normal. Voltar a uma conversa de 400 mil tokens depois do almoço custa uma regravação de 400 mil tokens.

**Como confirmar.** Achado "Contexto regravado em vez de relido do cache", que separa os motivos: pausa, troca de modelo, outra causa.

**Correção.**
- **Pausa.** Antes de uma pausa longa em conversa grande, feche a tarefa: grave o estado em arquivo e use `/clear` na volta. Dentro do uso do plano, o cache da conversa principal dura uma hora; depois que o plano estoura, cinco minutos.
- **Troca de modelo.** Escolha o modelo no início. Evite alternar no meio de conversa grande.
- **Outra causa.** Ligar ou desligar plugin, conectar ou remover servidor MCP e mudar o effort no meio da sessão também invalidam. Faça esses ajustes entre sessões.

**O que se perde.** Nada.

Fonte: /prompt-caching.

---

## carga-fixa

**Por que pesa.** A carga inicial entra em toda sessão e é relida em toda chamada. O relatório separa a base do aplicativo, que não dá para mexer, da parte que a pessoa controla: listagem de skills, nomes de ferramentas e conectores, instruções de servidores MCP, arquivos de memória e hooks de início de sessão.

**Como confirmar.** Achado "Carga inicial alta em toda sessão"; `/context` mostra a ocupação por categoria; `/doctor` estima o custo da listagem de skills.

**Correção.** Comece pela maior parcela listada no achado e siga a seção correspondente: `skills`, `mcp`, `claude-md` ou `hooks`. No app desktop, conectores ligados na conta também entram na carga; desligue na sessão os que não vai usar.

**O que se perde.** Depende do item removido. A regra é manter no escopo global só o que é usado em vários projetos.

---

## hooks

**Por que pesa.** Hooks de `SessionStart` e `UserPromptSubmit` podem colocar texto no contexto, e esse texto fica na conversa e é relido nas chamadas seguintes. Um hook que injeta mil tokens por mensagem acrescenta trinta mil tokens em trinta mensagens. Saídas acima de 10 mil caracteres são salvas em arquivo e substituídas por uma prévia, o que limita o estrago por execução.

**Como confirmar.** Achado "Hooks injetando texto no contexto", com evento, origem provável e volume. `/hooks` lista os hooks ativos e de onde vêm (usuário, projeto, plugin).

**Correção.**
- Hook de plugin: desligue o plugin onde ele não é necessário. `/plugin` desliga no escopo escolhido. Para desligar no global e ligar em um projeto, deixe `false` em `enabledPlugins` no `~/.claude/settings.json` e `true` no `.claude/settings.json` do projeto.
- Hook próprio: reduza o que ele imprime, ou restrinja o `matcher`.
- `"disableAllHooks": true` desliga todos de uma vez. Use para testar se o problema é esse.

**O que se perde.** O que o plugin fazia: skills, comandos e automações dele naquele escopo.

**Como desfazer.** Volte o valor em `enabledPlugins` ou restaure o backup.

Fonte: /hooks, /settings.

---

## saidas-grandes

**Por que pesa.** Uma saída de 12 mil tokens (um arquivo inteiro, um log, uma página web, uma captura de tela) fica no contexto e é relida até a conversa ser limpa.

**Como confirmar.** Achados "Saídas de ferramenta muito grandes" e "Muitas imagens no contexto"; linha "Ferramentas que mais trouxeram texto".

**Correção.**
- Peça leituras pontuais: "leia só a função X", "mostre as últimas 100 linhas do log", "liste só os testes que falharam".
- Trabalho que gera muita saída (busca ampla, leitura de documentação, rodar a suíte de testes) vai para um subagente: ele lê tudo e devolve um resumo. Veja `subagentes` para não pagar o modelo caro nisso.
- Prefira ferramentas de linha de comando (`gh`, `aws`, `gcloud`) a servidores MCP equivalentes quando elas existirem.
- Em automação de navegador, ler o texto da página custa menos do que tirar capturas de tela a cada passo.
- Cole o texto do erro em vez do print do erro.
- Para saídas repetitivas, um hook `PreToolUse` pode filtrar o resultado, por exemplo mantendo só as últimas 100 linhas de um teste.

**O que se perde.** Nada, se o pedido for bem delimitado.

Fonte: /costs.

---

## subagentes

**Por que pesa.** As chamadas de um subagente contam no mesmo limite. Por padrão ele herda o modelo da conversa, então uma busca simples delegada sai no Opus. O cache de subagentes dura cinco minutos.

**Como confirmar.** Achado "Subagentes rodando no mesmo modelo caro" e a linha "Subagentes" do resumo.

**Correção.**
- Agentes próprios: defina `model: haiku` ou `model: sonnet` no cabeçalho do arquivo em `~/.claude/agents/` ou `.claude/agents/`.
- A opção mais transparente é o ajudante do kit (`ajudante-haiku`): ele só tem ferramentas de leitura, aparece com o próprio nome na tela e vem com um aviso ao fim da resposta. Veja a seção "O ajudante no Haiku" do SKILL.md.
- Agente de busca embutido: um agente próprio chamado `Explore` com `model: haiku` substitui o embutido. Avise a pessoa de que o nome na tela continua o mesmo, então ela não vê que o modelo mudou.
- Padrão para os demais, também sem aviso na tela: variável `CLAUDE_CODE_SUBAGENT_MODEL` (por exemplo `sonnet`), no bloco `env` do settings.json. Sozinha ela não muda os agentes embutidos `Explore` e `Plan`; com `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` ela vale para todos.
- Ordem de prioridade: o modelo pedido na chamada, depois o do arquivo do agente, depois a variável, depois o modelo da conversa.
- Times de agentes gastam cerca de sete vezes mais que uma sessão comum. Use só quando o paralelismo compensar.

**O que se perde.** Subagentes mais baratos erram mais em tarefas que exigem julgamento. Mantenha o modelo maior em agentes de revisão e de planejamento.

**Como desfazer.** Remova a variável ou a linha `model` do agente.

Fonte: /sub-agents, /costs.

---

## skills

**Por que pesa.** O nome e a descrição de cada skill entram em toda sessão. O orçamento dessa listagem é de cerca de 1% da janela de contexto, uns 8 mil caracteres em um modelo de 200 mil tokens. Quando estoura, as descrições das skills menos usadas são cortadas: o nome continua lá, mas o Claude não sabe mais quando usar a skill. O problema é duplo: tokens gastos e skills que param de funcionar.

**Como confirmar.** Achado "Skills demais na listagem", com o total, os maiores grupos e quantas nunca foram usadas. `/doctor` estima o custo da listagem e `/skill-doctor` mostra o uso por skill.

**Correção.**
- Desinstale as que nunca foram usadas. Antes de apagar uma pasta em `~/.claude/skills/`, mova para fora (por exemplo `~/skills-guardadas/`) em vez de excluir.
- Skills de um projeto só vão para `.claude/skills/` daquele projeto.
- Para manter instalada sem pagar a descrição, a configuração `skillOverrides` aceita o modo `name-only`. Confira a sintaxe em /skills antes de editar.
- Pacotes que instalam dezenas de skills de uma vez são a causa mais comum. Fique com as três ou quatro que usa.

**O que se perde.** A skill deixa de ser sugerida automaticamente. Ainda pode ser chamada pelo nome, se continuar instalada.

**Como desfazer.** Mova a pasta de volta.

Fonte: /skills.

---

## claude-md

**Por que pesa.** Os arquivos CLAUDE.md são carregados inteiros no início de toda sessão. Importar outros arquivos com `@` não reduz o custo: o conteúdo importado entra junto.

**Como confirmar.** Linhas "Memória" do inventário. A documentação recomenda menos de 200 linhas por arquivo.

**Correção.**
- Deixe no CLAUDE.md só o que vale para toda sessão: comandos do projeto, convenções, o que não fazer.
- Instruções de um fluxo específico viram skill, que só carrega quando usada.
- Regras que valem para uma pasta vão para `.claude/rules/`, com escopo por caminho.
- `/memory` abre os arquivos para edição.

**O que se perde.** Nada, se o conteúdo movido continuar acessível por skill ou regra.

Fonte: /memory, /costs.

---

## mcp

**Por que pesa.** As definições das ferramentas MCP são adiadas por padrão, mas os nomes das ferramentas e as instruções de cada servidor entram em toda sessão. Cada resposta de ferramenta MCP também entra no contexto.

**Como confirmar.** Linha "Servidores MCP" do inventário, com o escopo de cada um. `/mcp` mostra o estado; `/context` mostra a ocupação.

**Correção.**
- `/mcp` desliga um servidor no projeto atual.
- Servidor usado em um projeto só deve ser configurado no escopo local ou de projeto (`.mcp.json`), não no de usuário.
- Se a variável `ENABLE_TOOL_SEARCH` estiver como `false`, todas as definições são carregadas no início. Remova a variável para voltar ao padrão.

**O que se perde.** As ferramentas daquele servidor nas sessões em que ele estiver desligado.

Fonte: /mcp, /costs.

---

## chave-api

**Por que pesa.** Com `ANTHROPIC_API_KEY` definida, o Claude Code usa a chave e cobra pelo preço da API, em vez de usar o plano.

**Como confirmar.** O relatório avisa quando a variável está no ambiente ou no bloco `env` do settings.json.

**Correção.** Remova a variável do perfil do terminal ou do settings.json, se a intenção for usar o plano. Não imprima nem copie o valor da chave.

**O que se perde.** Nada, se a pessoa tem plano. Quem usa a chave de propósito deve manter.

Fonte: https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan

---

## Medição manual (sem Python)

1. Peça à pessoa para rodar `/usage` e colar o resultado: ele mostra o consumo da sessão, os limites do plano e a divisão por skills, subagentes, plugins e servidores MCP.
2. Peça `/context` em uma sessão recém-aberta: a ocupação antes do primeiro pedido é a carga inicial.
3. Leia `~/.claude/settings.json` e o `.claude/settings.json` do projeto: `model`, `modelSettings`, `enabledPlugins`, `env`, `hooks`.
4. Conte as pastas em `~/.claude/skills/` e as linhas de cada CLAUDE.md.
5. `/hooks` e `/mcp` listam o que está ativo.

Com isso dá para preencher os achados de modelo, effort, carga inicial, hooks, skills, CLAUDE.md e MCP. Conversas longas e regravações de cache só aparecem com o script.
