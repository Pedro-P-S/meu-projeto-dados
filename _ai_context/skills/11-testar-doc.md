# Arquivo: skills/11-testar-doc.md

## /testar-doc
Quando eu digitar `/testar-doc` (idealmente em uma janela de chat limpa contendo apenas o `00-rules.md` e o `<DOC_MESTRE_CONTEXTO>`), aja como um Arquiteto Sênior que acabou de assumir o projeto sem nenhum contexto prévio além do que está escrito no documento.

**Não escreva código e não reescreva o documento.** Responda estritamente aos 4 pontos abaixo:
1. **Resumo de Compreensão:** Em 5 a 8 linhas, o que este sistema faz, de onde vêm os dados, qual é a arquitetura atual e o que já está pronto vs. o que falta fazer.
2. **Ambiguidades e Contradições Detectadas:** Aponte qualquer conflito dentro do próprio documento (ex.: uma coluna usada em uma fórmula DAX da Seção 5 que não existe na Seção 3, um relacionamento na Seção 4 com chave ausente, ou um grão mal definido).
3. **Pontos de Alucinação Forçada:** Se você fosse obrigado a implementar a próxima tarefa do backlog da Seção 1 agora mesmo, quais regras de negócio, tipos de dados, caminhos de arquivos ou comportamentos de borda você **teria que inventar/supor** porque o documento omitiu?
4. **Perguntas de Saneamento:** As perguntas diretas que eu preciso responder para corrigirmos essas lacunas no `<DOC_MESTRE_CONTEXTO>` antes de seguir codando.
