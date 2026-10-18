# Arquivo: skills/10-compactar.md

## /compactar
Quando eu digitar `/compactar`, faça uma poda cirúrgica no `<DOC_MESTRE_CONTEXTO>` para reduzir o consumo de tokens sem perder nenhuma trava técnica que sustenta o projeto.

### O que é INTOCÁVEL (Proibido remover ou alterar)
1. **Seção 3:** Nomes exatos de tabelas, grão, nomes de colunas, tipos de dados e **Contratos de Funções Python** (caminhos, assinaturas com type hints, entradas e saídas).
2. **Seção 4:** Chaves (`PK`/`FK`), cardinalidades e direções de filtro/join.
3. **Seção 5:** **Fórmulas literais completas** de SQL, DAX e equações matemáticas.
4. **Seção 7.1 e 7.2:** Decisões técnicas ativas e **Rotas Descartadas** com seus motivos técnicos exatos (memória anti-retrabalho).

### O que DEVE ser Removido ou Comprimido
1. Histórico narrativo de etapas passadas (mantenha na Seção 1 apenas a fotografia atual e os próximos 5 passos).
2. Corpos de código Python que tenham vazado para dentro do Doc Mestre (converta-os estritamente para assinaturas de contrato conforme a Regra de Ouro nº 3).
3. Pendências da Seção 7.3 que já foram resolvidas (Regra de Ouro nº 5).
4. Explicações verbosas de colunas ou métricas cujo próprio nome ou fórmula literal já seja autoexplicativo.
5. Repetições da mesma regra em múltiplas seções.

### Formato de Entrega
1. O novo `<DOC_MESTRE_CONTEXTO>` completo e enxuto em um bloco markdown pronto para copiar.
2. Um resumo de auditoria listando seção por seção o que foi removido ou comprimido (para eu aprovar antes de substituir meu arquivo oficial).
3. Contagem aproximada de palavras **Antes vs. Depois**.
