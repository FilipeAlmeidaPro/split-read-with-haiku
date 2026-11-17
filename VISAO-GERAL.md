# Visão geral: o que é o quê

Este arquivo separa três coisas que costumam ser misturadas: o que o Claude já faz sozinho, o que a skill `auditoria-de-tokens` é, e o que ela não é.

## 1. O que o Claude já tem, sem instalar nada

| O quê | Onde | O que mostra ou faz | O que falta |
|---|---|---|---|
| `/usage` | Claude Code | Consumo da sessão e limites do plano. Segundo a documentação, também divide o consumo por skills, subagentes, plugins e servidores MCP. | Não olha o histórico de várias sessões nem aponta a causa. |
| `/context` | Claude Code | O que ocupa o contexto da sessão aberta. | Só a sessão atual. |
| Configurações > Uso | Chat e app | Quanto resta da janela de cinco horas e do limite semanal. | Não diz o que gastou. |
| Skill embutida `explain-usage` | App desktop, em algumas instalações | Um gráfico de para onde foram os tokens da sessão atual. | Uma sessão só, sem correção, com pesos aproximados. |
| Controles: `/model`, `/effort`, `/clear`, `/compact`; no chat, o seletor de modelo e de esforço | Claude Code e chat | São os botões que de fato reduzem o gasto. | O Claude não aperta nenhum deles sozinho. |
| Automatismos: cache, carga adiada de ferramentas MCP, compactação quando o contexto enche | Claude Code | Barateiam a releitura e evitam que a conversa estoure. | Não escolhem modelo mais barato, não baixam o esforço e não limpam a conversa entre tarefas. |

Resumo: o Claude já mede a sessão atual e já tem todos os botões. Ele não diz qual botão apertar no seu caso.

## 2. O que a skill é

Uma pasta com instruções e três programas pequenos. Nada além disso.

| Arquivo | O que é |
|---|---|
| `SKILL.md` | As instruções que o Claude segue: medir primeiro, entregar três mudanças, dizer o que não é problema. |
| `scripts/auditar_claude_code.py` | Lê as configurações e até 30 dias de registros de sessão do Claude Code e calcula para onde o custo foi. |
| `scripts/analisar_export_chat.py` | Lê o histórico exportado do chat e mostra quais conversas mais pesaram. |
| `scripts/estimar_arquivo.py` | Estima quanto um arquivo pesa antes de ser anexado. |
| `references/correcoes.md` | Para cada problema, a correção exata, o que se perde e como desfazer. |
| `references/modo-chat.md` | A entrevista e as correções do chat, com o caminho dos cliques. |
| `references/como-os-tokens-sao-gastos.md` | A explicação do porquê, com a tabela de preços e as fontes. |
| `references/exemplos.md` | Exemplos de resposta nos dois modos. |

Para usar, a pessoa escreve "audite meus tokens". O Claude roda o programa, lê o resultado e responde neste formato:

1. Resumo em três linhas: quanto foi gasto, onde foi parar e a causa principal.
2. As três mudanças de maior impacto. Cada uma traz o número da pessoa, a ação exata, o que ela perde e o ganho esperado.
3. O que não é problema no caso dela.
4. Como conferir, uma semana depois, se funcionou.

## 3. O que a skill não é

- **Não troca de modelo sozinha.** A conversa principal do Claude Code não muda de modelo por conta própria, e nenhuma skill consegue fazer isso. A skill mostra onde o modelo caro está sobrando; quem troca é a pessoa.
- **Não economiza nada só por estar instalada.** Ela é um diagnóstico. A economia vem das mudanças que a pessoa aplica depois.
- **Não mexe em configuração sem confirmação.** Os programas só leem. Qualquer edição é mostrada antes e tem backup.
- **Não calcula o limite do plano.** A fórmula não é pública. Os percentuais usam os preços públicos da API para comparar causas entre si.
- **Não lê o texto das conversas.** Só tamanhos, contagens e nomes de modelos, ferramentas e pastas.
- **Não é gratuita em tokens.** Instalada e parada, custa cerca de 50 tokens por sessão. Uma auditoria completa gasta alguns milhares.

## 4. Por que vale ter mesmo assim

- **Histórico em vez de uma sessão.** Padrões como "a maior parte do custo vem de conversas acima de 150 mil tokens" só aparecem olhando semanas de uso.
- **Causa e correção juntas.** Cada achado vem com o comando ou o clique exato, o custo da mudança e o caminho de volta.
- **Ordem de prioridade.** As causas saem ordenadas por custo, então a pessoa começa pela que mais rende.
- **Descarta o que não se aplica.** A seção "o que não é problema" evita que a pessoa perca tempo arrumando o que quase não pesa.
- **Cobre o chat com dados.** O histórico exportado mostra quais conversas pesaram. Não encontramos nada embutido que faça isso.

## 5. Como ela resolve o "não sei qual modelo usar"

A dúvida costuma ser respondida com uma regra genérica. A skill responde com os números de quem perguntou.

Ela mostra quanto do custo foi em cada modelo, quantos pedidos feitos no modelo caro eram tarefas curtas e quanto os subagentes gastaram herdando esse modelo. Com isso a recomendação sai específica, por exemplo: Sonnet como padrão, Opus só nas sessões de arquitetura, subagentes de busca no Haiku. Cada troca vem com o ganho estimado e com o que se perde.

Ela também mostra quando o modelo não é o problema. Às vezes o que pesa é a conversa que nunca é limpa, e trocar de modelo resolveria pouco. Como as causas saem ordenadas por custo, a pessoa vê isso antes de mexer no que não importa.

A regra que sobra para o dia a dia é curta:

| Modelo | Quando | Custo em relação ao Opus |
|---|---|---|
| Haiku | Trabalho mecânico: formatar, extrair, buscar, resumir | Cerca de 40 vezes menor |
| Sonnet | Padrão: escrever, revisar, analisar, programar | Metade |
| Opus | Difícil: problema sem caminho claro, arquitetura, decisão cara | Referência |
| Fable | No plano Pro, só com créditos de uso, cobrados à parte | O dobro |

Troque de modelo no início da sessão. Trocar no meio de uma conversa grande faz o contexto inteiro ser regravado.

## 6. Estado atual

- O modo Claude Code foi testado em uma máquina, com dados reais.
- O leitor do histórico do chat só foi testado com dados sintéticos.
- Os caminhos de menu do chat vieram das páginas de ajuda e não foram conferidos na interface.
- Windows não foi testado.
