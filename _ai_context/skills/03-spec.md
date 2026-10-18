# Arquivo: skills/03-spec.md

## /spec
Quando eu digitar `/spec`, sintetize tudo o que já foi decidido na conversa e no `<DOC_MESTRE_CONTEXTO>` em uma especificação técnica enxuta e uma lista ordenada de tarefas. **Não faça perguntas de entrevista:** se faltar algo essencial, registre como pendência explícita.

### Processo
1. Use estritamente os nomes de tabelas, colunas e termos de negócio já padronizados no `<DOC_MESTRE_CONTEXTO>`.
2. Foque a validação nas **bordas do sistema** (totais batendo com relatórios oficiais/contabilidade, invariantes de grão, casos de borda e testes `pytest` nos contratos), não em detalhes internos de implementação.
3. Fatie o trabalho em tarefas verticais pequenas (que caibam em uma única sessão de chat e terminem em algo executável/verificável).

### Modelo de Entrega (entregue em bloco markdown `docs/spec-<nome>.md`)
```markdown
# Spec: <Nome do Projeto ou Módulo>

## 1. Problema e Solução
- **Problema:** O que dói hoje, do ponto de vista de quem usa.
- **Solução e Entrega:** O artefato final que será construído e como será consumido.

## 2. Requisitos e Casos de Uso
1. Como <papel>, quero <ação/cálculo>, para <decisão/benefício>.
(Liste de 5 a 10 itens cobrindo o escopo fechado).

## 3. Regras de Implementação e Contratos
- Fontes e esquemas utilizados.
- Regras de cálculo, filtros obrigatórios e tratamento de exceções/nulos.
- Módulos afetados (sem trechos longos de código; apenas contratos e fórmulas críticas).

## 4. Plano de Validação (Critérios de Aceite)
- **Conferência de Totais/Reconciliação:** Como provar que os números batem com a fonte oficial.
- **Invariantes de Dados:** Checagens de unicidade de chave, ausência de explosão de join e nulos proibidos.
- **Testes Automatizados:** Casos de borda que devem ter cobertura via `pytest`.

## 5. Fora do Escopo
- O que foi explicitamente deixado de fora desta entrega.

## 6. Pendências Abertas
- [ ] Dúvidas ou bloqueios que precisam ser resolvidos antes de tarefas específicas.

## 7. Backlog Fatiado (Ordem de Execução)
- [ ] **T1:** <Título curto> | Entrega verificável: <o que roda/valida no fim> | Depende de: Nenhuma
- [ ] **T2:** <Título curto> | Entrega verificável: <o que roda/valida no fim> | Depende de: T1
```

Ao final, entregue também o recorte das 5 primeiras tarefas formatado para colar diretamente na Seção 1 do `<DOC_MESTRE_CONTEXTO>`.
