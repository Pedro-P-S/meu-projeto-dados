<DOC_MESTRE_CONTEXTO>
# DOC MESTRE DE CONTEXTO
**Projeto:** _a preencher_ | **Versão:** 0.1 | **Atualizado em:** AAAA-MM-DD

> Documento de estado presente. Remova os marcadores `_a preencher_` conforme as definições forem fechadas via `/grill-me`, `/arquitetura` e `/explore-data`.

---

## 1. Visão Geral e Status Atual
- **Objetivo do projeto (1-2 frases):** _a preencher_
- **Público/Consumidor final:** _a preencher_
- **Última etapa concluída:** Nenhuma (projeto em inicialização)
- **Backlog imediato (detalhar no máximo as próximas 5 fatias verticais):**
  1. [ ] _a preencher_ (Depende de: nenhuma)
  2. [ ] _a preencher_ (Depende de: item 1)

---

## 2. Fontes de Dados (Data Sources) e Infraestrutura
| ID Fonte | Tipo (Oracle, Parquet, CSV, API, Excel) | Caminho / Tabela Bruta (sem credenciais) | Janela / Atualização | Responsável / Origem |
|---|---|---|---|---|
| `_a preencher_` | `_a preencher_` | `_a preencher_` | `_a preencher_` | `_a preencher_` |

- **Variáveis de Ambiente Obrigatórias (apenas nomes):** `_a preencher_ (ex.: DB_HOST, DB_USER, DATA_DIR)`
- **Ambiente de Execução:** `Python _versão_ | Bibliotecas principais: _ex.: pandas, polars, sqlalchemy, pytest_`
- **Estrutura de Diretórios do Projeto:**
```text
_a preencher_
```

---

## 3. Dicionário de Dados, Esquema e Contratos Python

### 3.1. Entidades / Tabelas / DataFrames
#### Entidade: `_nome_exato_da_tabela_ou_df_`
- **Camada:** `_Bruta (Ingestão) | Tratada (Transformação) | Final (Saída/BI)_`
- **Grão (uma linha representa exatamente):** `_a preencher_`
- **Chave Primária (PK):** `_a preencher_` | **Volume/Período estimado:** `_a preencher_`

| Coluna (nome exato) | Tipo de Dado | Classe (ID, Dimensão, Métrica, Data) | % Nulos / Qualidade | Regra de Transformação / Limpeza Aplicada |
|---|---|---|---|---|
| `_a preencher_` | `_a preencher_` | `_a preencher_` | `_a preencher_` | `_a preencher_` |

### 3.2. Contratos de Módulos Python (Regra de Ouro nº 3 — Somente Assinaturas)
- **Módulo:** `caminho/do/arquivo.py`
  - **Assinatura:** `def nome_funcao(param1: tipo, param2: tipo) -> tipo_retorno`
  - **Entrada esperada:** `_entidades e colunas obrigatórias_`
  - **Saída / Efeito colateral:** `_dataframe retornado ou arquivo gravado com seu schema_`
  - **Verificação / Teste:** `_comando pytest ou script de validação_`

---

## 4. Modelagem e Relacionamentos
- **Fluxo de Dados Ponta a Ponta:** `_fonte -> ingestão -> transformação -> camada de saída -> Power BI_`

| Tabela Origem (1 / Dimensão) | PK | Tabela Destino (N / Fato) | FK | Cardinalidade | Direção de Filtro / Tipo de Join | Ativo? |
|---|---|---|---|---|---|---|
| `_a preencher_` | `_pk_` | `_a preencher_` | `_fk_` | `1:N` | `Única (Dim -> Fato) / LEFT JOIN` | `Sim` |

---

## 5. Métricas, Cálculos e Regras de Negócio (Fórmulas Literais)

### Regra / Métrica: `[_nome_exato_da_medida_ou_regra_]`
- **Definição de Negócio:** `_o que calcula e como trata casos de borda/nulos_`
- **Tabela de Hospedagem / Pasta (se Power BI):** `_Medidas | Pasta: _nome_ | Formato: _ex.: R$ #,##0.00_`
- **Fórmula Literal (SQL, DAX ou Equação Matemática):**
```dax
-- Substituir pela fórmula literal completa (Regra de Ouro nº 4)
_a preencher_
```

---

## 6. Camada Visual / Interface / Outputs
### Página / Aba / Artefato de Saída: `_nome_da_pagina_ou_arquivo_`
| Componente / Visual | Tipo (KPI, Gráfico, Matriz, Slicer, Export) | Campos (Eixo/Linhas/Colunas) | Medidas / Valores | Filtros de Página/Visual Aplicados |
|---|---|---|---|---|
| `_a preencher_` | `_a preencher_` | `_a preencher_` | `_a preencher_` | `_a preencher_` |

---

## 7. Decisões Técnicas, Rotas Descartadas e Pendências

### 7.1. Decisões Ativas (Parâmetros e Arquitetura Fechados)
- **[AAAA-MM-DD]** _a preencher_

### 7.2. Rotas Descartadas (Memória Anti-Retrabalho)
| O que foi tentado / considerado | Motivo técnico exato do descarte |
|---|---|
| `_a preencher_` | `_a preencher_` |

### 7.3. Pendências e Dúvidas em Aberto
- [ ] _a preencher_
</DOC_MESTRE_CONTEXTO>
