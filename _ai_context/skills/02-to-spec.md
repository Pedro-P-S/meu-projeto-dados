# SKILL `/spec` — to-spec (Matt Pocock, adaptada ao chat-only)

> Cole dentro de `<SKILLS_ATIVAS>`. Pode rodar na mesma conversa do `/grill` (ela sintetiza o que já foi discutido).

## Objetivo
Transformar o contexto da conversa e o entendimento do projeto (Doc Mestre) em uma **spec**. **NÃO entreviste o usuário**: apenas sintetize o que você já sabe. (A única pergunta permitida é a do passo 2.)

Sem tracker externo: a spec é publicada como arquivo em `.scratch/<feature-slug>/spec.md` (um `aplicar.py` cria a pasta e o arquivo). Status: `ready-for-agent`.

## Processo

1. **Entenda o estado atual** pelo Doc Mestre (Seções 2 a 6). Use o vocabulário do **glossário** (Seção 8) em toda a spec e respeite os **ADRs** (Seção 7) da área que vai mexer. Se precisar ver um arquivo existente, entregue o script que o gera para colar (regra 3.3), sem inventar.

2. **Esboce os *seams* de teste** — os pontos onde o comportamento será verificado. Prefira seams que já existem aos novos. Use o **mais alto possível**. Se precisar de novos, proponha no ponto mais alto que conseguir. Quanto menos seams no projeto, melhor; o ideal é um só. No nosso ambiente, um seam é tipicamente: o contrato de uma função pública, a tabela/arquivo de saída final, uma view SQL ou uma medida DAX, sempre verificados por **checagens OK/FALHOU** (regra 2). **Confirme com o usuário numa única pergunta** se esses seams batem com a expectativa dele (com a sua recomendação, para ele responder "sim").

3. **Escreva a spec** neste modelo e entregue via `aplicar.py`:

```
## Problema (Problem Statement)
O problema, do ponto de vista de quem o tem.

## Solução (Solution)
A solução, do ponto de vista de quem a usa.

## Histórias de Usuário (User Stories)
Lista numerada LONGA, cobrindo todos os aspectos da feature, no formato:
1. Como <ator>, eu quero <funcionalidade>, para que <benefício>
(ex.: 1. Como analista de conciliação, eu quero ver a diferença entre o saldo contábil e o saldo da operação, para que eu encontre rápido onde há divergência)

## Decisões de Implementação
- Módulos que serão criados/alterados
- Interfaces (contratos) desses módulos
- Esclarecimentos técnicos do usuário
- Decisões de arquitetura, mudanças de esquema, contratos de API, interações específicas
NÃO inclua caminhos de arquivo nem trechos de código: envelhecem rápido.
Exceção: se um protótipo produziu um trecho que codifica uma decisão com mais precisão que a prosa (máquina de estados, esquema, formato de tipo), coloque-o dentro da decisão e diga que veio de protótipo, só a parte rica em decisão.

## Decisões de Teste
- O que faz um bom teste aqui: verificar comportamento externo (a saída), não detalhes internos; comparar caminhos independentes (regra 2).
- Quais módulos/saídas serão testados e as checagens OK/FALHOU de cada um
- Exemplos prévios no projeto (testes ou checagens parecidos já existentes)

## Fora de Escopo
O que não faz parte desta spec.

## Notas Adicionais
Qualquer outra informação relevante.
```

4. Cabeçalho do arquivo: título, `Status: ready-for-agent`, data. Sem dados reais em nenhuma parte (só nomes de tabelas/colunas, tipos e regras).

5. Encerre recomendando `/tickets` (na mesma conversa).

▶️ Termine com `▶️ Sua vez:` dizendo qual a próxima ação do usuário.
