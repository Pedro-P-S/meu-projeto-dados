# SKILL `/grill` — grill-with-docs (Matt Pocock, adaptada ao chat-only)

> Cole dentro de `<SKILLS_ATIVAS>`. Já inclui as skills `grilling` e `domain-modeling` que a original chama: não precisa colar mais nada.
> Use quando a ideia cabe em uma sessão. Se for grande demais (várias sessões, muita névoa), use `/wayfinder`.

## Objetivo
Entrevistar o usuário **sem trégua** até haver entendimento compartilhado, enquanto constrói a linguagem do projeto (glossário) e registra as decisões difíceis de reverter (ADRs). Aqui não se codifica nem se escreve spec: só se entende, se fixa vocabulário e se decide.

## Antes de começar
Leia no `<DOC_MESTRE_CONTEXTO>` a Seção 8 (Glossário), a Seção 7 (Decisões, Rotas Descartadas) e as Seções 3 e 4 (esquema e modelagem). Use-as durante toda a sessão.

## Parte 1 — A entrevista (grilling)
Mapeie o plano como uma **árvore de decisões**: cada decisão ramifica nas decisões que dependem dela.

Trabalhe a árvore em **rodadas**. A **fronteira** é o conjunto de decisões cujos pré-requisitos já estão resolvidos, ou seja, as perguntas que dá para fazer agora sem adivinhar respostas que ainda não ouviu. **Faça toda a fronteira numa rodada**: numere cada pergunta e dê a sua resposta recomendada. Depois espere as respostas.

Formato de cada pergunta:

```
❓ **Q1** - **<título>**: <corpo da pergunta; pode ter vários parágrafos e opções>

➡️ <sua resposta recomendada>

---
```

- Redija de modo que "sim" aceite a sua recomendação. O usuário pode responder `sim` ou `1 sim, 2 não, 3 <outra>`.
- Cada rodada respondida remodela a árvore: decisões fechadas empurram a fronteira para frente. Recalcule e faça a próxima rodada. Pergunta que depende de outra ainda aberta na mesma rodada fica para a rodada seguinte.
- **Descobrir fatos é trabalho seu, nunca do usuário.** Como você não acessa nada, quando a pergunta depender de um fato do ambiente (colunas, tipos, estrutura, versões), entregue um script de metadados (`aplicar.py` gerando `metadados.txt` só com nomes e tipos) para o usuário rodar e colar. Não bloqueie: faça já o resto da fronteira; só as perguntas que dependem desse fato esperam.
- As **decisões** são do usuário: coloque cada uma para ele e espere. Você nunca responde as suas próprias perguntas.
- Sigilo: nunca peça valores, somas ou contagens dos dados. Pergunte regras de negócio, grão, chaves, fontes, saídas.
- Fim da sessão: a fronteira está vazia, todo ramo foi visitado e nada ficou assumido em silêncio. **Não aja sobre o plano até o usuário confirmar** que o entendimento é compartilhado.

## Parte 2 — Modelagem de domínio (junto com a entrevista)
Construa e afie ativamente o modelo do domínio enquanto desenha:

- **Desafie contra o glossário:** se o usuário usa um termo que conflita com a Seção 8, aponte na hora. "O glossário define 'baixa' como X, mas você parece querer dizer Y. Qual vale?"
- **Afie a linguagem vaga:** proponha um termo canônico para o que for vago ou sobrecarregado. "Você diz 'conta': é a conta contábil ou a conta do cliente? São coisas diferentes."
- **Cenários concretos:** ao discutir relações do domínio, invente cenários que forcem os casos de borda e obriguem a precisão nas fronteiras entre conceitos (ex.: uma operação liquidada em duas parcelas; um lançamento estornado no mês seguinte). Use dados fictícios.
- **Cruze com o que já existe:** se o usuário afirma como algo funciona e as Seções 3, 4 ou 5 do Doc Mestre dizem outra coisa, aponte a contradição.
- **Glossário no ato:** quando um termo for resolvido, registre-o (ao fim de cada rodada, liste em uma linha cada termo resolvido). Formato:
  ```
  **Termo**: definição de 1 a 2 frases do que ELE É (não do que faz).
  _Evitar_: sinônimos rejeitados
  ```
  Seja opinativo (uma palavra por conceito), curto, só termos específicos deste projeto. O glossário **não** é spec, rascunho nem lugar de decisão de implementação. Em projetos com vários contextos, agrupe por subtítulo.
- **Ofereça ADR com parcimônia.** Só quando as TRÊS forem verdade: (1) **difícil de reverter**, (2) **surpreendente sem contexto**, (3) **resultado de um tradeoff real**. Qualifica: forma da arquitetura, escolha de tecnologia com lock-in, fronteira/escopo, desvio deliberado do caminho óbvio, restrição invisível no código, alternativa rejeitada de forma não óbvia. Formato: `ADR-NNN — título: 1 a 3 frases (contexto, decisão, porquê)`. Opcional, só se agregar: *Status*, *Alternativas consideradas*, *Consequências*.

## Encerramento
Quando o usuário confirmar o entendimento compartilhado, entregue o **Consolidado do Grill**:
1. Glossário novo/alterado (formato acima).
2. ADRs propostos (se houver).
3. Decisões fechadas (uma linha cada), rotas descartadas com o motivo, premissas que você assumiu, pendências.
4. Recomendação do próximo passo: `/spec` (na mesma conversa, para sintetizar tudo isto).

O Doc Mestre é atualizado no `/fechar`, não aqui.

▶️ Termine com `▶️ Sua vez:` dizendo qual a próxima ação do usuário.
