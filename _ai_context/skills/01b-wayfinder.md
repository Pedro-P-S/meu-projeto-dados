# SKILL `/wayfinder` — wayfinder (Matt Pocock, adaptada ao chat-only)

> Cole dentro de `<SKILLS_ATIVAS>` **junto com `01-grill-with-docs.md`** (esta skill chama `grilling` e `domain-modeling`, que estão lá). As skills `research` e `prototype`, que o wayfinder também chama, já estão resumidas abaixo.
> Use quando uma ideia é grande demais para uma sessão e está envolta em névoa: o caminho até o **destino** ainda não é visível.

## O que é
Wayfinding é **achar o caminho**, não correr até o destino. A skill desenha o caminho como um **mapa compartilhado** (arquivos Markdown) e resolve os **tickets de decisão** (perguntas cuja resposta é uma decisão, não fatias de construção) **um por sessão**, até o caminho ficar claro.

O destino varia por esforço e nomeá-lo é o primeiro ato: pode ser uma spec para entregar a `/spec`, uma decisão a fixar antes de planejar, ou uma mudança no lugar (ex.: migração de estrutura de dados).

## Planejar, não fazer
Cada ticket resolve uma decisão. O mapa termina quando o caminho está claro, sem nada mais a decidir antes de alguém ir fazer. A vontade de "já fazer" costuma ser o sinal de que chegou à borda do mapa e é hora de passar para `/spec`. Salvo se as **Notas** do esforço disserem o contrário, produza decisões, não entregáveis.

## Referir por nome
Todo mapa e ticket tem um **nome** (o título). Em tudo que o usuário lê, cite pelo nome, nunca por número solto. O arquivo/número vai junto do nome, nunca no lugar dele.

## O mapa (`.scratch/<esforço>/map.md`)
É um **índice**, não um depósito: lista as decisões tomadas e aponta para os tickets que guardam o detalhe. Uma decisão vive em um único lugar, o ticket. Os tickets abertos **não** aparecem no mapa: são os arquivos de `issues/` ainda não resolvidos.

```markdown
## Destino
<o que significa chegar ao fim deste mapa: a spec, decisão ou mudança. Uma ou duas linhas; toda sessão se orienta por isto antes de escolher um ticket.>

## Notas
<domínio; skills que toda sessão deve consultar; preferências fixas deste esforço>

## Decisões até agora
<!-- uma linha por ticket resolvido: o bastante para julgar relevância -->
- [<título do ticket resolvido>](issues/NN-slug.md): <resumo de uma linha da resposta>

## Ainda não especificado
<!-- névoa dentro do escopo que ainda não dá para virar ticket; gradua conforme a fronteira avança -->

## Fora de escopo
<!-- trabalho descartado deste esforço; nunca gradua -->
```

## Os tickets (`.scratch/<esforço>/issues/NN-slug.md`, a partir de `01`)
Cada ticket é um arquivo; o corpo é a pergunta, **dimensionada para uma conversa**:

```markdown
# NN: <título>

**Type:** research | prototype | grilling | task
**Status:** aberto
**Blocked by:** NN, NN   (ou "Nenhum")

## Pergunta
<a decisão ou investigação que este ticket resolve>
```

- Bloqueio: o ticket está **desbloqueado** quando todos os tickets listados em `Blocked by` estão `resolvido`. A **fronteira** = tickets abertos, desbloqueados e não iniciados; vale o de menor número.
- Status: `aberto` → `em-andamento` (marque antes de qualquer trabalho) → `resolvido`.
- A resposta não fica no corpo original: é registrada ao resolver, sob `## Resposta`. Ativos criados ao resolver (protótipos, scripts) ficam em arquivos e são citados no ticket, não colados.
- Só existem rótulos de wayfinder aqui; nunca marque tickets como `ready-for-agent`: são decisões, não implementação.

## Tipos de ticket
Todo ticket é **HITL** (o usuário participa e responde por si; você nunca responde o lado dele) ou **AFK** (você resolve sozinho).

- **research** (AFK): levantar um fato fora do projeto de que uma decisão depende. **No chat você não navega**: responda com o que sabe, cite a fonte primária provável (documentação oficial, especificação) e marque **`[não verificado]`**. Se a decisão depender criticamente do fato, abra um ticket `task` com o passo mínimo de confirmação (você entrega o link/script exato).
- **prototype** (HITL): elevar a fidelidade da conversa com um artefato barato, rudimentar e **descartável** (um esboço, um stub, uma lógica) para o usuário reagir. No chat: um único script Python ou arquivo HTML, com **dados sintéticos**, marcado `PROTÓTIPO`, que roda com um comando, sem persistência, mostrando o estado após cada ação. Sem testes nem polimento. Usado quando a questão central é "como deve se comportar/parecer".
- **grilling** (HITL): conversa. É o caso padrão. Siga `01-grill-with-docs.md` (entrevista + modelagem de domínio).
- **task** (HITL ou AFK): trabalho manual que precisa acontecer antes de uma *decisão* (levantar a estrutura de uma tabela, preparar um acesso). É o único tipo que *faz* em vez de decidir. Automatize você (script `aplicar.py` de metadados) sempre que possível; senão, passo a passo exato. A resposta registra o que foi feito e os fatos resultantes de que tickets posteriores dependem.

## Névoa e fora de escopo
O mapa é **deliberadamente incompleto**: não trace o que ainda não enxerga. Além dos tickets vivos está a **névoa**: decisões que você sabe que virão mas não consegue pôr em palavras com precisão porque dependem de perguntas abertas. Ela vai em **Ainda não especificado**.

**Névoa ou ticket?** O teste é se você consegue **formular a pergunta com precisão agora**, não se consegue responder agora. Pergunta nítida, mesmo bloqueada → ticket. Não nítida → névoa. Não fatie a névoa em pedaços de ticket: ela é mais grossa e um trecho pode virar vários tickets, ou nenhum. Resolver um ticket clareia a névoa à frente e gradua o que agora dá para especificar, um por vez.

**Fora de escopo:** o destino fixa o escopo. O que está além dele não é névoa. Fica na seção **Fora de escopo** (resumo + motivo) e nunca gradua. Ticket que já existe e se revela fora do escopo: marque `resolvido` com a nota "fora de escopo" e deixe uma linha na seção. Não entra em "Decisões até agora", que registra só o caminho percorrido.

## Como invocar (duas modalidades)
Em ambas: **nunca resolva mais de um ticket por sessão** (exceção: tickets `research`).

### A) Traçar o mapa (o usuário traz uma ideia solta)
1. **Nomeie o destino.** Siga `01-grill-with-docs.md` para fixar a que este mapa chega (spec, decisão ou mudança). O destino define o escopo, então vem primeiro.
2. **Mapeie a fronteira.** Faça grilling de novo, **em largura**: abra o espaço inteiro em vez de aprofundar um fio, expondo as decisões abertas e os primeiros passos possíveis agora. **Se não aparecer névoa** (o caminho já está claro e cabe em uma sessão), não precisa de mapa: pare e pergunte como o usuário quer prosseguir (provavelmente `/grill` ou `/spec`).
3. **Crie o mapa** (`map.md`): Destino e Notas preenchidos, "Decisões até agora" vazio, a névoa esboçada.
4. **Crie os tickets que já dá para especificar**, numerados em ordem, com os bloqueios (`Blocked by`) escritos já com os números corretos. O que não dá para especificar fica na névoa.
5. **Resolva já os tickets `research`** desta sessão (não há subagentes no chat), de forma curta, no próprio arquivo, em `## Resposta`, marcando `[não verificado]` quando for o caso.
6. Pare: traçar o mapa é o trabalho de uma sessão e não resolve nada além de pesquisa. Entregue tudo num único `aplicar.py` que cria `map.md` e os arquivos de ticket, com `CHECK` de que cada arquivo foi gravado.

### B) Trabalhar o mapa (o usuário traz o mapa)
Em `<TAREFA_ATUAL>` vêm o `map.md` e, opcionalmente, o ticket escolhido. Sem ticket, **você escolhe**: o primeiro da fronteira.
1. Carregue o **mapa** (visão de baixa resolução). Escolha o ticket e marque `em-andamento`.
2. Resolva-o **como o tipo do `Type`** manda (leia o campo, o corpo nunca diz o tipo). Peça o corpo completo de qualquer ticket relacionado ou resolvido só se precisar. Na dúvida, grilling + modelagem de domínio.
3. **Registre a resolução:** acrescente `## Resposta`, marque `resolvido` e acrescente uma linha (resumo + link) em "Decisões até agora" do `map.md`.
4. **Novos tickets:** crie os que surgiram; gradue a névoa que agora dá para especificar (e apague o trecho graduado de "Ainda não especificado"); se algo se revelar além do destino, mande para **Fora de escopo**; se a decisão invalida outras partes do mapa, atualize ou remova esses tickets.
5. Entregue tudo num `aplicar.py` (edições exatas no `map.md` e no ticket + novos arquivos) com `CHECK` por edição.
6. Quando não restarem tickets e o caminho estiver claro, o mapa terminou: recomende `/spec` com o Destino como ponto de partida.

▶️ Termine com `▶️ Sua vez:` dizendo qual a próxima ação do usuário.
