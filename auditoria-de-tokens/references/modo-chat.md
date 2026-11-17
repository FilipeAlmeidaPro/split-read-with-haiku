# Modo chat

Para quem usa o Claude pelo site, pelo app desktop ou pelo celular. Caminhos de menu conferidos nas páginas de ajuda em 17/11/2026. A interface muda; se um caminho não existir mais, diga isso e descreva o que procurar.

## 1. Coleta

### A. Histórico exportado

1. Configurações > Privacidade > Exportar dados. O link chega por e-mail em alguns minutos.
2. A pessoa baixa o `.zip` e anexa o `conversations.json`, ou o zip inteiro se couber.
3. Rode `python3 scripts/analisar_export_chat.py <arquivo> --dias 30`.

O script não mostra o texto das conversas, só títulos, contagens e tamanhos. Com `--anonimo`, nem os títulos. A exportação não informa modelo, raciocínio, ferramentas, Projetos nem imagens: o resultado é um piso, bom para comparar conversas e hábitos.

Se o arquivo for grande demais para anexar, peça para a pessoa rodar o script no próprio computador e colar o resultado.

### B. Tela de uso

Configurações > Uso mostra a sessão atual (janela de cinco horas) e o limite semanal, com o horário em que cada um zera. Pergunte qual dos dois costuma acabar primeiro:

- **Acaba a janela de cinco horas:** o problema é intensidade. Sessões de trabalho pesadas, com modelo caro, conversa longa ou Research.
- **Acaba o semanal:** o problema é volume. Muitos dias de uso contínuo; o ganho vem de baixar o custo de cada conversa.

### C. Entrevista

Faça as seis perguntas de uma vez, numeradas, para a pessoa responder em uma mensagem só.

1. Qual modelo fica selecionado na maior parte do tempo? Você muda o nível de esforço ou o Thinking?
2. Você tem conversas que duram dias, às quais sempre volta? Quantas mensagens elas costumam ter?
3. Você anexa arquivos? De que tipo e tamanho? Reanexa os mesmos arquivos em conversas diferentes?
4. Quais conectores e ferramentas ficam ligados (busca na web, Research, Drive, e-mail, outros)? Com que frequência usa o Research?
5. Como você costuma pedir: várias mensagens curtas em sequência, ou um pedido completo? Pede para refazer documentos ou artefatos inteiros quando quer mudar um detalhe?
6. Quando o limite acaba, você está fazendo o quê? Usa também o Claude Code ou o app desktop?

## 2. Interpretação

Cada resposta aponta para uma correção da seção 3. Ordene pelo que a pessoa relatou com mais intensidade e pelo que o histórico exportado mostrou.

| Sinal | Correção |
|---|---|
| Opus selecionado para tudo; Fable no plano Pro | Modelo |
| Esforço alto ou Thinking sempre ligado | Esforço |
| Conversas de dias, com dezenas de mensagens; no export, poucas conversas concentram a releitura | Conversa nova com resumo de passagem |
| PDFs e planilhas grandes; os mesmos arquivos em várias conversas | Arquivos e Projetos |
| Muitos conectores ligados; Research frequente | Conectores e Research |
| Mensagens picadas; "refaz tudo" para mudar um detalhe | Jeito de pedir |
| Usa Claude Code também | Rodar o modo Claude Code; o limite é o mesmo |

## 3. Correções

### Modelo

- O seletor fica ao lado do botão de enviar. A escolha vale para a conversa.
- Sonnet para o dia a dia: escrever, revisar, analisar, programar.
- Haiku para o simples: reformatar, traduzir, resumir, pergunta direta.
- Opus para o difícil: raciocínio longo, problema sem caminho claro, texto em que cada detalhe importa.
- Só fale do Fable se a pessoa usa. No plano Pro ele não entra no limite: consome créditos de uso, cobrados à parte pelo preço da API, e custa o dobro do Opus. Vale conferir em Configurações > Uso se os créditos estão ligados e definir um teto mensal de gasto.

O que se perde: em tarefas difíceis, o modelo menor pode exigir mais correções. Se a pessoa notar retrabalho, sobe o modelo naquela conversa.

### Esforço

- Clique no nome do modelo > Esforço. Nível mais baixo rende mais uso; nível mais alto dá respostas mais elaboradas, demora mais e gasta mais. Recomende o nível médio como padrão e o baixo para tarefas mecânicas.
- Em modelos com o botão Thinking, desligue quando não precisar de raciocínio estendido.
- No Opus 5.5 e no Sonnet 5.5 o raciocínio fica sempre ligado; o controle é o nível de esforço.

### Conversa nova com resumo de passagem

A ajuda oficial recomenda começar conversas novas para assuntos novos, e avisa que conversas longas consomem mais do limite. Use o resumo abaixo para não perder o fio.

Peça na conversa antiga:

```
Resuma esta conversa para eu continuar em uma conversa nova. Máximo de 20 linhas:
1. Objetivo
2. Decisões já tomadas e por quê
3. Estado atual (o que está pronto)
4. Próximos passos
5. Restrições e preferências que eu dei
6. Nomes de arquivos, links e termos que preciso manter
Não inclua o que foi descartado.
```

Cole o resultado como primeira mensagem da conversa nova.

Complementos:

- Memória e busca em conversas: em Configurações, a opção de buscar e referenciar conversas deixa a pessoa perguntar "o que decidimos sobre X?" em vez de recolar contexto.
- Regra prática: conversa nova a cada assunto, e também quando a mesma tarefa passar de umas 15 a 20 mensagens.

### Arquivos e Projetos

- Rode `scripts/estimar_arquivo.py` nos arquivos que a pessoa costuma anexar. Um PDF usa de 1.500 a 3.000 tokens por página, e fica na conversa.
- Anexe só o trecho necessário: as páginas que importam, a aba da planilha, o texto em vez do print.
- Faça todas as perguntas sobre um arquivo grande em uma mensagem.
- Arquivo que volta sempre vai para um Projeto. A ajuda oficial informa que o conteúdo de Projetos fica em cache e conta menos no limite quando reutilizado, e que o cache expira depois de um tempo sem uso.

### Conectores e Research

- Cada conector ocupa espaço na conversa. Em "+" ou "/" > Conectores > Acesso a ferramentas, deixe ligados só os que vai usar naquela conversa. A escolha vale só para ela.
- Os modos são Automático (padrão), Sempre disponível (carregado no início de toda conversa) e Sob demanda (só carrega quando o Claude procura). Para conector de uso raro, Sob demanda.
- Research consome o limite mais rápido. Ligue no botão "+" só quando a pergunta pedir pesquisa extensa; para uma dúvida pontual, a busca na web comum basta.

### Jeito de pedir

Tirado das boas práticas oficiais:

- Planeje antes e junte pedidos relacionados em uma mensagem.
- Dê o contexto todo de uma vez: objetivo, público, formato, restrições. Cada correção posterior relê a conversa inteira.
- Releia antes de enviar.
- Para mudar um detalhe de um documento ou artefato, peça a alteração só naquele trecho.

## 4. Entrega

Plano com no máximo três mudanças, no formato do SKILL.md. Para cada uma: onde clicar, o que a pessoa perde, e o que observar em Configurações > Uso na semana seguinte. Termine com "o que não é problema no seu caso".

Sobre o "ganho esperado": use o número da simulação quando o histórico foi analisado. Para modelo, use a proporção de preço (o Sonnet custa metade do Opus; o Haiku, uma fração pequena). Para o que não dá para medir, diga isso em vez de inventar um número.

Se a pessoa não exportou o histórico, diga que o plano se baseia no relato dela e ofereça refazer com os dados reais.
