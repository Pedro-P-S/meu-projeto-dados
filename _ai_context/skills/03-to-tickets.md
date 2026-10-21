# SKILL `/tickets` — to-tickets (Matt Pocock, adaptada ao chat-only)

> Cole dentro de `<SKILLS_ATIVAS>`. Pode rodar na mesma conversa do `/spec`.

## Objetivo
Quebrar um plano, uma spec ou a conversa em um conjunto de **tickets**: fatias verticais *tracer bullet*, cada uma declarando os tickets que a **bloqueiam**.

Sem tracker externo: os tickets são arquivos em `.scratch/<feature-slug>/issues/NN-slug.md`, **um arquivo por ticket**, numerados a partir de `01` em ordem de dependência (bloqueadores primeiro). Nunca um arquivo único com todos.

## Processo

### 1. Reúna o contexto
Trabalhe com o que já está na conversa. Se o usuário passou a spec (colada ou em `<TAREFA_ATUAL>`), leia-a inteira.

### 2. Considere o que já existe (opcional)
Use o Doc Mestre (contratos da Seção 3, modelagem da 4) para entender o estado atual. Títulos e descrições usam o vocabulário do **glossário** (Seção 8) e respeitam os ADRs (Seção 7). Procure oportunidades de **pré-refatoração**: *"torne a mudança fácil, depois faça a mudança fácil"*. Se precisar ver um arquivo, entregue o script que o gera para colar.

### 3. Rascunhe as fatias verticais
- Cada fatia corta um caminho **estreito mas COMPLETO** por todas as camadas que o projeto tiver (ex.: leitura → transformação → saída → checagem; ou consulta SQL → medida DAX → visual): **vertical**, NÃO uma fatia horizontal de uma camada só.
- Uma fatia concluída é **demonstrável ou verificável sozinha** (por checagens OK/FALHOU).
- Cada fatia cabe em **uma conversa nova** (um ticket por conversa).
- Pré-refatoração vem primeiro.

Dê a cada ticket seus **bloqueios**: os tickets que precisam terminar antes. Sem bloqueios = pode começar já.

**Refatorações amplas são a exceção à fatia vertical.** Uma mudança mecânica (renomear coluna, mudar o tipo de um campo compartilhado) cujo raio de impacto espalha por todo o projeto, quebrando muitos pontos de uma vez, não vira um tracer bullet. Sequencie como **expandir–contrair**: (1) *expandir*: adicione a forma nova ao lado da antiga, nada quebra; (2) *migrar* os pontos de uso em lotes pelo raio de impacto (por módulo/pasta), cada lote um ticket bloqueado pelo "expandir"; (3) *contrair*: remova a forma antiga quando nenhum uso restar, em um ticket bloqueado por todos os lotes. Se nem os lotes ficam verdes sozinhos, mantenha a sequência e faça um ticket final de "integrar e verificar".

### 4. Questione o usuário
Apresente a quebra como lista numerada. Para cada ticket mostre:
- **Título**: nome curto e descritivo
- **Bloqueado por**: quais tickets (se houver)
- **O que entrega**: o comportamento ponta a ponta que o ticket faz funcionar

Pergunte, **em uma rodada só, com a sua recomendação para cada uma** (o usuário responde "sim" ou por número):
- A granularidade está certa? (grossa demais / fina demais)
- Os bloqueios estão corretos: cada ticket depende só de quem realmente o bloqueia?
- Algum ticket deve ser fundido ou dividido?

Itere até o usuário aprovar a quebra.

### 5. Publique os tickets
Entregue UM `aplicar.py` que grava um arquivo por ticket neste modelo, mais `CHECK` de que cada arquivo foi criado:

```
# <NN>: <Título do ticket>

**O que construir:** o comportamento ponta a ponta que este ticket faz funcionar, do ponto de vista de quem usa, não uma lista de implementação por camada.

**Bloqueado por:** os números/títulos dos tickets que o bloqueiam, ou "Nenhum (pode começar já)".

**Status:** ready-for-agent

- [ ] Critério de aceite 1
- [ ] Critério de aceite 2
```

- **Todo ticket deve conter, nos critérios de aceite, as checagens OK/FALHOU** que provam que ele funciona (regra 2): é assim que o usuário valida sem ler código. Cada checagem compara caminhos independentes.
- Evite caminhos de arquivo e trechos de código: envelhecem rápido. Exceção: trecho de protótipo que codifica uma decisão com mais precisão que a prosa (diga que veio de protótipo; só a parte essencial).
- Trabalhe a **fronteira**: qualquer ticket cujos bloqueios estejam todos `done`. Numa cadeia linear, de cima para baixo.
- **NÃO feche nem altere a spec** de origem.
- O mesmo script copia o ticket `01` (ou o primeiro sem bloqueios) para `_ai_context/02-task.md`, para a próxima conversa já começar nele.

▶️ Termine com `▶️ Sua vez:` dizendo qual a próxima ação do usuário (normalmente: `/fechar` para registrar glossário/decisões no Doc Mestre e depois abrir uma conversa nova com `/implementar`).
