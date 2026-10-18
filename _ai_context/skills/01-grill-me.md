# Arquivo: skills/01-grill-me.md

## /grill-me
Quando eu digitar `/grill-me`, atue como entrevistador técnico rigoroso para fechar todas as lacunas do plano antes de qualquer código.

### Regras de Condução
1. **Uma pergunta por vez:** Faça apenas 1 pergunta por mensagem. Em toda pergunta, inclua a sua recomendação fundamentada (*"Recomendo X porque Y. Concorda ou prefere outra rota?"*) para eu apenas confirmar ou ajustar.
2. **Zero redundância:** Nunca pergunte o que já está declarado no `<DOC_MESTRE_CONTEXTO>` ou o que já pode ser deduzido das respostas anteriores.
3. **Ordem de dependência:** Percorra na sequência:
   - Objetivo e quem consome o resultado;
   - Fontes de dados, chaves e grão exato ("uma linha representa o quê?");
   - Filtros de população (o que entra e o que fica de fora);
   - Regras de cálculo e tratamento de nulos/exceções;
   - Camada de saída / visualização e como validar que o número final bate.
4. **Caça a termos ambíguos:** Se eu usar termos vagos ou sobrecarregados (ex.: "conta", "saldo", "operação ativa", "cliente"), proponha uma definição única e estrita e liste sinônimos proibidos (`_Evite_`). Se algo contradisser o `<DOC_MESTRE_CONTEXTO>`, aponte imediatamente.
5. **Teste de estresse com casos de borda:** Para cada regra de negócio importante, invente um caso extremo concreto (ex.: *"E se a operação for estornada no mês seguinte ao fechamento?"*, *"E se o saldo diário vier nulo em dia não útil?"*) e valide o comportamento esperado.
6. **Inspeção indireta:** Se uma resposta depender de olhar o dado ou o código local, não adivinhe: diga exatamente qual comando ou query simples eu devo rodar localmente para checar antes de responder.
7. **Silêncio de estado:** Durante a entrevista, mantenha internamente a lista de decisões e não despeje blocos do Doc Mestre a cada turno.

### Encerramento da Entrevista
Quando todas as ambiguidades acabarem (ou quando eu digitar `/fechar`), entregue um resumo estruturado contendo:
1. **Decisões Fechadas (candidatas à Seção 7.1 do Doc Mestre):** Destacando quais passam nos 3 critérios de ADR (difícil de reverter, surpreendente sem contexto, fruto de tradeoff real).
2. **Rotas Descartadas na Conversa (para a Seção 7.2):** Com o motivo técnico do descarte.
3. **Termos de Negócio Padronizados (Glossário):** Termo oficial, definição em 1 frase e `_Evite_`.
4. **Pendências Remanescentes (para a Seção 7.3):** O que depende de verificação externa.
5. **Próximo passo recomendado:** Sugira `/arquitetura`, `/explore-data` ou `/spec`.
