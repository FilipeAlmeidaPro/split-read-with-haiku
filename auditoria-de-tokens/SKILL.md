---
name: auditoria-de-tokens
description: Mede para onde vão os tokens no Claude Code e no chat e monta um plano para o limite render mais. Use quando falarem de limite, uso, tokens, custo ou plano acabando rápido.
---

# Auditoria de tokens

Quem bate no limite do plano quase nunca sabe por quê. Dica genérica ("use conversas curtas", "escolha o modelo certo") não resolve, porque a causa muda de pessoa para pessoa: para uma é a conversa de 600 mil tokens que nunca é limpa, para outra é um plugin que injeta texto em toda mensagem, para outra é o modelo padrão. Esta skill existe para **medir primeiro e recomendar depois**. Cada recomendação sai com o número que a justifica e com o tamanho do ganho esperado.

## Princípios

1. **Evidência antes de conselho.** Não recomende nada que os dados da pessoa não sustentem. Se um problema clássico não aparece nos números dela, diga que não é o caso dela. Isso vale mais do que uma lista de dez dicas.
2. **Maior impacto primeiro, três mudanças por vez.** Uma lista longa não é aplicada. Entregue as três de maior impacto e deixe o resto para a próxima medição.
3. **Nada muda sem confirmação e sem backup.** Os scripts só leem. Antes de editar qualquer arquivo de configuração, mostre o que vai mudar, o que a pessoa perde com a mudança e como desfazer, e copie o arquivo original.
4. **Seja honesto sobre os números.** A Anthropic não publica a fórmula do limite dos planos. As porcentagens de custo do relatório usam os preços públicos da API para comparar causas entre si. Apresente como estimativa, nunca como conta exata.
5. **Privacidade.** Os scripts medem tamanhos e contagens e não leem o texto das conversas. Não copie trechos de conversas para a resposta. Se a pessoa for compartilhar o relatório, rode com `--anonimo`.
6. **Explique os termos na primeira vez.** Token, contexto, cache e subagente precisam de uma frase cada, dentro do próprio item em que aparecem. Muita gente que usa o Claude não programa.

## Passo 0: descobrir onde você está

- **Claude Code** (terminal, aba Code do app, extensão de IDE): você roda comandos na máquina da pessoa e existe a pasta `~/.claude`. Siga o modo Claude Code.
- **Chat** (claude.ai, app desktop ou celular): os comandos rodam num ambiente isolado, sem os arquivos da pessoa. Siga o modo chat.

Na dúvida, rode `python3 scripts/auditar_claude_code.py --so-config`. Se ele disser que não encontrou a pasta `.claude`, é o modo chat.

O limite é compartilhado entre o chat, o Claude Code e o app desktop. Ao terminar um modo, pergunte se a pessoa também usa o outro, a não ser que ela já tenha dito.

## Modo Claude Code

1. **Medir.** Rode, a partir da pasta desta skill:

   ```bash
   python3 scripts/auditar_claude_code.py --dias 14
   ```

   Use `python` se `python3` não existir. Use `--dias 30` se a pessoa usa pouco. O script lê também a configuração de projeto da pasta em que a sessão está; para apontar outra, use `--projeto <pasta>`. O script leva poucos segundos, não altera nada e não acessa a rede. Sem Python, faça a medição manual descrita no fim de `references/correcoes.md`.

2. **Ler o relatório inteiro e não despejar.** A resposta tem três partes:
   - Resumo de três linhas: quanto foi usado, onde foi parar e qual é a causa principal.
   - Os três achados de maior impacto. Para cada um: o que é, em uma frase sem jargão; a evidência, com os números do relatório; o que fazer; o que a pessoa perde com a mudança.
   - Uma pergunta: quais ela quer aplicar agora.

3. **Corrigir.** Para cada achado escolhido, leia a seção de mesmo identificador em `references/correcoes.md`. Ela traz por que pesa, como confirmar, a correção exata, o que se perde e como desfazer. Comandos que só a pessoa pode digitar (`/model`, `/effort`, `/clear`) você ensina; edição de arquivo você faz depois da confirmação, com backup.

4. **Fechar com a próxima medição.** Diga quais números devem mudar (por exemplo, carga inicial, parcela de chamadas com contexto longo, peso por modelo) e sugira rodar de novo em sete dias. Indique `/usage` e `/context` para acompanhar ao vivo.

### Como ler o relatório sem errar

- **Olhe a coluna "Parte do custo", não o volume bruto.** A leitura de cache domina o volume, mas custa de 5% a 10% de uma leitura normal. No Opus, um milhão de tokens de saída custa o mesmo que cem milhões lidos do cache.
- **Carga inicial tem uma parte que a pessoa controla e uma que não.** O relatório separa as duas. Não prometa reduzir a base do aplicativo.
- **Configuração de hoje e uso do período podem divergir.** O inventário mostra o que está configurado agora; os achados de uso mostram o que aconteceu. Se a pessoa já desligou algo, os registros ainda vão mostrar o passado. Diga isso.
- **Achado sem parcela estimada não é necessariamente pequeno.** Ele só não pôde ser medido em custo.
- **Trocar de modelo no meio de uma conversa grande regrava o contexto inteiro.** Recomende a troca no início da sessão ou depois de `/clear`.
- **As parcelas se sobrepõem. Não some.** Uma chamada de subagente no Opus, feita com a conversa grande, entra em três achados ao mesmo tempo. No "ganho esperado" de cada item, use a frase de impacto do achado e avise que os ganhos não se somam.
- **Achados com a mesma correção viram um item só.** "Conversas que continuam depois de ficarem grandes" e "Compactação só acontece no limite" se resolvem juntos.
- **Sem número, não invente.** Se o relatório não estima o ganho, use a proporção da tabela de preços (o Sonnet custa metade do Opus) ou diga que não dá para estimar.
- **Poucos dados, pouca certeza.** Com menos de cinco sessões no período, diga que a amostra é pequena.

## Modo chat

No chat não há arquivo de configuração para ler. Os dados vêm de três fontes, da mais forte para a mais fraca:

- **A. Histórico exportado (dados reais).** A pessoa pede a exportação em Configurações > Privacidade > Exportar dados, recebe um `.zip` por e-mail e anexa o `conversations.json` (ou o zip). Rode `python3 scripts/analisar_export_chat.py <arquivo>`. O resultado mostra quais conversas mais pesaram, quanto do gasto veio de conversas longas e de anexos, e simula quanto ela economizaria abrindo conversas novas.
- **B. Tela de uso.** Peça um print ou os números de Configurações > Uso (sessão atual e limite semanal).
- **C. Entrevista.** Seis perguntas em `references/modo-chat.md`.

Ofereça A logo no início, porque o e-mail demora alguns minutos, e faça C enquanto isso. Se a pessoa não quiser exportar, siga só com B e C e diga que o diagnóstico fica menos preciso. Quando o relato e o histórico divergirem, vale o histórico; diga a diferença à pessoa.

Duas ferramentas extras:

- **Arquivos.** Quando a pessoa anexar ou mencionar arquivos grandes, rode `python3 scripts/estimar_arquivo.py <arquivos>` para mostrar quanto cada um pesa e quanto custa mantê-lo numa conversa longa.
- **Resumo de passagem.** Quando a conversa atual estiver longa, ofereça o resumo para continuar em conversa nova. O modelo está em `references/modo-chat.md`.

A entrega é um plano com no máximo três mudanças. Cada uma diz onde clicar e o que observar em Configurações > Uso na semana seguinte. As correções do chat, com o caminho de cada clique, estão em `references/modo-chat.md`.

## Formato da resposta

```
**Resumo:** [quanto, onde foi, causa principal]

**1. [Achado em linguagem simples]**
- O que os seus dados mostram: [números]
- O que fazer: [ação exata]
- O que você perde: [custo da mudança, ou "nada"]
- Ganho esperado: [estimativa, com a palavra "cerca de"]

**2.** ...
**3.** ...

**O que não é problema no seu caso:** [um ou dois itens clássicos que os dados descartam]

**Como conferir:** [que número deve mudar, onde olhar e quando]

Quais você quer aplicar agora?
```

A seção "o que não é problema" é o que separa uma auditoria de uma lista de dicas. Não a pule.

## Referências

- `references/como-os-tokens-sao-gastos.md`: leia quando precisar explicar o porquê (o modelo relê tudo a cada chamada, como o cache funciona, o que conta no limite).
- `references/correcoes.md`: uma seção por achado do relatório do Claude Code, mais a medição manual.
- `references/modo-chat.md`: entrevista, interpretação, correções com o caminho dos cliques e o resumo de passagem.
- `references/exemplos.md`: exemplos de boa resposta nos dois modos.
