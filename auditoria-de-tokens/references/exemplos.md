# Exemplos de boa resposta

Os números são inventados. Servem para mostrar o nível de detalhe esperado: evidência com número, ação exata, custo da mudança e o que não é problema.

## Exemplo 1: Claude Code

Pedido: "meu limite do Pro acaba antes do almoço, o que eu faço?"

Resposta depois de rodar `auditar_claude_code.py --dias 14`:

> **Resumo:** em 14 dias foram 19 sessões e 2.140 chamadas ao modelo, equivalentes a cerca de US$ 96 em preço de API. 91% desse custo foi no Opus, e 62% veio de chamadas feitas com a conversa acima de 150 mil tokens. A causa principal é conversa longa em modelo caro.
>
> **1. Você continua na mesma conversa depois que ela fica enorme**
> - O que os seus dados mostram: 7 das 19 sessões passaram de 150 mil tokens sem nenhuma limpeza. Nelas, cada chamada releu em média 280 mil tokens. A cada pedido seu o Claude faz várias chamadas, e todas releem a conversa inteira.
> - O que fazer: ao terminar uma tarefa, peça "grave em PROGRESSO.md o que foi feito, o que falta e os arquivos envolvidos", digite `/clear` e comece a próxima pedindo para ler esse arquivo. Para a compactação automática acontecer antes, `/autocompact 200000`.
> - O que você perde: o histórico detalhado da conversa. O arquivo guarda o que importa.
> - Ganho esperado: cerca de um terço do custo do período.
>
> **2. Tudo roda no Opus, que é o padrão do plano**
> - O que os seus dados mostram: 91% do custo no Opus. 44 dos seus 310 pedidos foram tarefas curtas, com até duas ferramentas.
> - O que fazer: `/model sonnet` para deixar o Sonnet como padrão. Abra no Opus só a sessão que for de arquitetura ou de bug difícil.
> - O que você perde: em problemas complexos o Sonnet pode precisar de mais correções.
> - Ganho esperado: a mesma sessão custa cerca de metade. Movendo metade do trabalho, cerca de 20% do total.
>
> **3. Subagentes também rodam no Opus**
> - O que os seus dados mostram: 480 chamadas de subagentes, 18% do custo, todas no Opus. A maioria é busca de arquivos.
> - O que fazer: criar `~/.claude/agents/Explore.md` com `model: haiku`, que substitui o agente de busca embutido. Posso criar o arquivo.
> - O que você perde: buscas um pouco menos espertas em bases de código confusas.
> - Ganho esperado: cerca de 15% do total, porque o Haiku custa uma fração do Opus.
>
> **O que não é problema no seu caso:** o CLAUDE.md tem 40 linhas e as 6 skills instaladas cabem na listagem com folga. Não há hooks injetando texto. Não vale a pena mexer nisso.
>
> Quais você quer aplicar agora?

Por que funciona: três itens, cada um com o número da pessoa; o custo de cada mudança está dito; a seção final descarta as dicas clássicas que não se aplicam.

## Exemplo 2: chat com histórico exportado

Pedido: "uso o Claude para escrever e pesquisar, pago o Pro e trava toda tarde."

Resposta depois de rodar `analisar_export_chat.py` e de duas perguntas (modelo e conectores):

> **Resumo:** nos últimos 30 dias você teve 52 conversas. Três delas concentram 88% de tudo que o modelo precisou reler. A causa principal são conversas que duram semanas com um PDF grande dentro.
>
> **1. Três conversas longas pesam mais que as outras 49 juntas**
> - O que os seus dados mostram: a conversa do relatório anual tem 96 mensagens suas e ficou 18 dias aberta. Cada mensagem nova nela relê cerca de 85 mil tokens.
> - O que fazer: peça o resumo de passagem (modelo abaixo) e continue em conversa nova. Repita a cada 15 ou 20 mensagens.
> - O que você perde: detalhes antigos que não entrarem no resumo. A conversa antiga continua lá para consulta.
> - Ganho esperado: a simulação com o seu histórico indica cerca de 70% menos releitura.
>
> **2. O PDF de 140 páginas é relido em toda mensagem**
> - O que os seus dados mostram: ele ocupa cerca de 35 mil tokens e foi anexado em duas conversas. Sozinho, responde por 41% da releitura.
> - O que fazer: coloque o PDF em um Projeto. O conteúdo de Projetos fica em cache e conta menos quando reutilizado. Quando a pergunta for sobre um capítulo, anexe só aquelas páginas.
> - O que você perde: nada.
>
> **3. Opus com esforço alto para revisar texto**
> - O que você contou: o Opus fica selecionado o dia todo, com esforço alto.
> - O que fazer: Sonnet como padrão; no nome do modelo > Esforço, deixe no nível médio. Suba para o Opus na conversa de estrutura do relatório.
> - O que você perde: em raciocínios longos, o Sonnet pode ser mais raso.
>
> **O que não é problema no seu caso:** as 49 conversas curtas quase não pesam, então não precisa economizar nas perguntas rápidas. Você só tem um conector ligado e não usa o Research.
>
> Na semana que vem, olhe em Configurações > Uso se a sessão de cinco horas passou a durar a tarde toda.

## Exemplo 3: resumo de passagem

Saída esperada quando a pessoa pede o resumo para continuar em conversa nova:

> **Objetivo:** fechar o relatório anual de 2026 para o conselho, com 12 páginas, até 28/11.
>
> **Decisões tomadas:**
> - Estrutura em 5 seções: resultados, clientes, produto, pessoas, plano de 2027.
> - Tom direto, sem adjetivos; números sempre com a fonte.
> - O gráfico de receita usa trimestres, não meses, porque o conselho compara com o orçamento trimestral.
>
> **Estado atual:** seções 1 e 2 prontas e revisadas. Seção 3 em rascunho, falta a parte de roadmap.
>
> **Próximos passos:** terminar a seção 3; escrever a 4 com os dados de pessoas; revisar o sumário executivo por último.
>
> **Restrições:** máximo de 12 páginas; nada de projeções sem intervalo; português do Brasil.
>
> **Manter:** arquivo `relatorio-2026-v3.docx`; termos "receita recorrente" e "clientes ativos" como definidos na seção 1.

Vinte linhas ou menos. Sem o que foi descartado, sem a história de como se chegou a cada decisão.
