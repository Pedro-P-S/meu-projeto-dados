# SKILL `/review` — code-review (Matt Pocock, adaptada ao chat-only)

> Cole dentro de `<SKILLS_ATIVAS>`. **Rode sempre em uma conversa NOVA**, sem o histórico da implementação (o original usa subagentes em paralelo justamente para um eixo não contaminar o outro).
> Mensagem inicial: `00-rules.md` + esta skill + Doc Mestre + a spec (e o ticket) + o conteúdo de `.scratch/<feature>/review.diff` (gerado pelo `/implementar`). Se faltar algo, peça de forma automatizada (script que gera o que falta), sem pedir dados.

## Objetivo
Revisão do diff entre `HEAD` e um ponto fixo, em **dois eixos**:
- **Padrões (Standards):** o código segue os padrões documentados do projeto?
- **Spec:** o código implementa fielmente o que a spec/ticket pediu?

Um mesmo código pode passar num eixo e falhar no outro: segue todos os padrões mas implementa a coisa errada (*Padrões passam, Spec falha*), ou faz exatamente o pedido quebrando as convenções (*Spec passa, Padrões falham*). Por isso os dois relatórios ficam **separados**.

## Processo

### 1. Fixe o ponto de comparação
O diff é `review.diff` (já gerado como `git diff <commit-anterior> HEAD`). Confirme que **não está vazio** e que traz os arquivos esperados do ticket. Se estiver vazio ou faltar, pare aqui e entregue o comando exato para gerar de novo (ex.: `git diff <ponto-fixo>...HEAD > .scratch/<feature>/review.diff`). Se o diff contiver algo que pareça dado real ou segredo, pare e avise (regra 1.2).

### 2. Identifique a fonte da spec
Nesta ordem: (1) a spec/ticket colados; (2) referência no texto do commit; (3) peça onde está. Se não houver spec, o eixo **Spec** é pulado e o relatório diz "sem spec disponível".

### 3. Identifique as fontes de padrões
Padrões documentados: `00-rules.md` (seções 3, 5 e 6: cirúrgico, simplicidade, Schema Drift, Zero Placeholders, contratos, fórmulas literais), o **Doc Mestre** (esquema, contratos, glossário, ADRs) e qualquer `CODING_STANDARDS.md`/`CONTRIBUTING.md` que o usuário colar.

Além do que o projeto documenta, o eixo Padrões **sempre** carrega a **linha de base de cheiros** abaixo (cheiros de código de Fowler, *Refactoring*, cap. 3), que vale mesmo quando o projeto não documenta nada. Duas regras:
- **O projeto vence:** um padrão documentado sempre vence; onde ele endossa algo que a linha de base marcaria, suprima o cheiro.
- **Sempre julgamento:** cada cheiro é uma heurística rotulada ("possível Feature Envy"), nunca violação dura. Ignore o que ferramenta já faz cumprir.

Cada cheiro: *o que é* → *como corrigir*:
- **Nome Misterioso**: nome que não revela o que faz/guarda. → renomear; se não sai nome honesto, o desenho está obscuro.
- **Código Duplicado**: a mesma lógica em mais de um trecho/arquivo da mudança. → extrair e chamar dos dois.
- **Inveja de Funcionalidade (Feature Envy)**: função que mexe mais nos dados de outro objeto do que nos seus. → mover para junto dos dados.
- **Aglomerado de Dados (Data Clumps)**: os mesmos campos/parâmetros andam sempre juntos. → agrupar em um tipo.
- **Obsessão por Primitivos**: texto/número fazendo papel de um conceito do domínio. → dar ao conceito um tipo pequeno.
- **Condicionais Repetidos (Repeated Switches)**: o mesmo `if/switch` sobre o mesmo tipo reaparece. → polimorfismo, ou um mapa compartilhado.
- **Cirurgia de Espingarda (Shotgun Surgery)**: uma mudança lógica exige edições espalhadas por muitos arquivos. → juntar o que muda junto em um módulo.
- **Mudança Divergente**: um arquivo/módulo é editado por vários motivos não relacionados. → dividir, para cada módulo mudar por um motivo.
- **Generalidade Especulativa**: abstração/parâmetro/gancho para necessidade que a spec não tem. → apagar; voltar a inline até aparecer necessidade real.
- **Cadeias de Mensagens**: navegação longa `a.b().c().d()` da qual o chamador não deveria depender. → esconder atrás de um método no primeiro objeto.
- **Intermediário (Middle Man)**: classe/função que só repassa. → cortar e chamar o alvo direto.
- **Herança Recusada**: subclasse que ignora ou sobrescreve quase tudo que herda. → trocar herança por composição.

### 4. Faça as duas passagens, **separadas**
Como o chat não tem subagentes, faça duas passagens independentes, **uma de cada vez, cada uma olhando só para as suas fontes**. Escreva a passagem **Padrões** sem usar a spec para julgar; depois a passagem **Spec** sem usar os padrões para julgar.

**Padrões — pergunta:** por arquivo/trecho: (a) cada lugar onde o diff viola um padrão documentado (cite o arquivo e a regra); (b) qualquer cheiro da linha de base (nomeie-o e cite o trecho). Distinga **violações duras** de **julgamentos**: quebras de padrão documentado podem ser duras; cheiros da linha de base são sempre julgamento. Ignore o que ferramenta já cobre. **Até 400 palavras.**

**Spec — pergunta:** (a) requisitos pedidos que estão **ausentes ou parciais**; (b) comportamento no diff que **não foi pedido** (aumento de escopo); (c) requisitos que **parecem implementados mas a implementação parece errada**. **Cite a linha da spec** em cada achado. Verifique também se **cada checagem OK/FALHOU do ticket existe e é independente** (não tautológica). **Até 400 palavras.**

### 5. Agregue
Apresente sob os títulos `## Padrões` e `## Spec`, sem fundir nem reordenar os achados: os eixos são separados de propósito. Termine com **uma linha de resumo**: total de achados por eixo e o pior problema **dentro de cada eixo**. Não eleja um vencedor entre eixos (é exatamente o reranking que a separação evita).

### 6. Correção em um único passo
Se houver achados, entregue já **um único `aplicar.py`** com as correções (violações duras e achados da Spec; os cheiros de "julgamento" só entram se o usuário responder `sim`, em uma pergunta única, com a sua recomendação). O script roda as checagens do ticket de novo e, com tudo OK, faz o commit local como no `/implementar`. Sem achados, diga "nada a corrigir".

▶️ Termine com `▶️ Sua vez:` dizendo qual a próxima ação do usuário.
