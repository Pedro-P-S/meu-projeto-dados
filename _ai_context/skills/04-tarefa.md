# Arquivo: skills/04-tarefa.md

## /tarefa
Quando eu digitar `/tarefa` (ou `/tarefa <número/nome da fatia>`), gere o arquivo `02-task.md` completo para a próxima sessão de trabalho, baseando-se nas Seções 1, 3, 5 e 7 do `<DOC_MESTRE_CONTEXTO>`.

### Regras
1. Se eu não especificar qual tarefa quero, selecione a próxima tarefa do backlog da Seção 1 que não esteja bloqueada por nenhuma pendência da Seção 7.3.
2. **Dimensionamento:** Se a tarefa escolhida for grande demais para uma única conversa de chat, divida-a em partes menores (`Parte A`, `Parte B`), entregue o `02-task.md` apenas da `Parte A` e liste as demais para atualizarmos o backlog.
3. **Trava de Esquema (Schema Drift Gate):** Preencha o campo *Entradas Disponíveis* usando exclusivamente os nomes exatos de tabelas, colunas, arquivos e contratos já presentes no `<DOC_MESTRE_CONTEXTO>`. Se faltar uma tabela ou definição necessária, aponte como bloqueio em *Dúvidas* em vez de inventar nomes.
4. **Critérios Verificáveis:** Cada critério de sucesso deve ser um comando concreto (`pytest`, script de checagem, query SQL de batimento ou teste visual em cartão do Power BI) que eu possa rodar localmente.
5. Indique quais arquivos `skills/*.md` eu devo colar em `<SKILLS_ATIVAS>` na próxima conversa para executar essa tarefa.

### Formato de Saída
Entregue um único bloco de código markdown contendo o `02-task.md` preenchido, pronto para copiar e colar na abertura do próximo chat.
