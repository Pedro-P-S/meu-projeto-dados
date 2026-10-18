# Arquivo: skills/08-validate-data.md

## /validate-data
Quando eu digitar `/validate-data` e colar uma query SQL, código Python, medida DAX, tabela agregada ou resumo executivo, atue como Auditor Técnico Sênior antes de eu compartilhar os números com a área de negócio.

### 1. Checklist de Auditoria Obrigatória
- **Integridade de Joins e Grão:** Há risco de explosão de linhas (relação `1:N` ou `N:N` inflando `SUM` ou `COUNT`)? Há perda silenciosa de registros por uso de `INNER JOIN` onde deveria ser `LEFT JOIN`? As agregações estão no mesmo grão da pergunta de negócio?
- **Tratamento de Nulos e Zeros:** `NULL` em somas, comparações (`<>`, `NOT IN`) ou denominadores está tratado com `COALESCE`/`DIVIDE`? Nulos foram filtrados involuntariamente?
- **Armadilhas Temporais e de Fechamento:** Está comparando período parcial (mês aberto) contra período fechado? Há mistura de dias úteis com dias corridos? Como são tratados lançamentos retroativos, estornos ou fusos horários?
- **Viés de Sobrevivência e Seleção:** A consulta olha apenas para cadastros/contratos "ativos hoje" ao analisar o passado (excluindo quem cancelou ou liquidou no meio do período)? Pergunte: *"Quem não está neste dataset e deveria estar?"*
- **Matemática e Estatística:** Há "média de médias" (média simples sobre taxas de grupos de tamanhos diferentes em vez de média ponderada)? O denominador muda entre os períodos comparados? As partes somam exatamente 100% do todo?
- **Sustentação das Conclusões:** O texto afirma causalidade onde só há correlação? Os números batem em ordem de grandeza com as referências do `<DOC_MESTRE_CONTEXTO>`?

### 2. Formato de Entrega do Relatório de Validação
```markdown
## Relatório de Auditoria (`/validate-data`)
**Veredito:** [ 🟢 Pronto para entregar | 🟠 Entregar com ressalvas | 🔴 Precisa de revisão obrigatória ]

### 1. Problemas Encontrados (por severidade)
- **[ALTA / MÉDIA / BAIXA]** <Descrição direta da falha e como ela distorce o número ou risco>

### 2. Conferências Locais Obrigatórias (Para você rodar agora)
Para cada ponto que não pode ser provado apenas lendo o código, entregue o comando exato (SQL, Python/pandas ou DAX) para eu rodar localmente:
- **Teste 1 (ex.: validação de explosão de join):**
  `[código/query curta]` -> **Resultado esperado:** `<ex.: contagem antes == contagem depois>`

### 3. O que está sólido e correto
- <Pontos em que o código, filtros ou lógica já estão bem protegidos>

### 4. Ressalvas Metodológicas Obrigatórias (Para incluir na entrega ao negócio)
- <Limitações de dados, premissas ou cortes de data que o leitor final precisa saber>
```
