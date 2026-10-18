# Arquivo: skills/05-explore-data.md

## /explore-data
Quando eu digitar `/explore-data`, ajude-me a perfilar, auditar a qualidade e documentar uma fonte de dados na **Seção 3 do `<DOC_MESTRE_CONTEXTO>`** sem nunca expor dados sensíveis reais no chat.

### Modo A: Eu ainda não tenho o resumo estatístico (Gerar Script Local)
Se eu apenas descrever a fonte (onde mora: Oracle/SQL, CSV/TXT, Excel ou Parquet; nomes de colunas conhecidos; grão esperado e volume aproximado):
1. Entregue um **script local sob medida** (Python com `pandas`/`polars` ou query SQL; se for Oracle, use `ALL_TAB_COLUMNS` para metadados e `SAMPLE` para tabelas gigantes) que eu rodarei na minha máquina.
2. **Regras de segurança e escala do script gerado:**
   - **Zero dados individuais:** Por padrão, o script só calcula e imprime agregados estatísticos e metadados (nunca imprime linhas reais, nomes ou CPFs; exemplos de valores só se acionada uma flag explícita `--com-valores` em colunas de baixa cardinalidade não sensíveis).
   - **Leitura eficiente:** Para arquivos grandes, suporte leitura em chunks ou amostragem parametrizável, avisando no output se a amostra for apenas do topo do arquivo (risco de viés temporal).
   - **Métricas calculadas pelo script:**
     * *Tabela:* total de linhas, total de colunas, linhas duplicadas exatas, unicidade da chave candidata (PK), período mínimo e máximo das colunas de data.
     * *Todas as colunas:* tipo físico, % de nulos, contagem de distintos, cardinalidade (`distintos / linhas`).
     * *Numéricas:* mín, máx, média, mediana, desvio-padrão, percentis (`p1, p5, p25, p75, p95, p99`), contagem de zeros, negativos e infinitos.
     * *Texto:* comprimento mín/máx, strings vazias, espaços nas pontas (leading/trailing), mistura de caixa (maiúscula/minúscula) e placeholders suspeitos (`N/A`, `TBD`, `NULL`, `999999`, `-1`, `0`).
     * *Datas:* mín, máx, nulas, datas no futuro e quebras/buracos na série temporal (ex.: dias úteis faltantes).

### Modo B: Eu colei o resumo agregado ou amostra sintética (Interpretar e Documentar)
Quando eu colar a saída agregada do script (ou uma amostra sintética/anonimizada):
1. Use exclusivamente o que foi colado. Tudo o que a amostra não permitir concluir deve ser marcado como `[NÃO VERIFICADO]`.
2. **Classifique cada coluna:** `Identificador (ID)`, `Dimensão` (agrupamento/filtro, baixa cardinalidade), `Métrica` (valor agregável), `Temporal`, `Texto Livre`, `Booleano` ou `Estrutural`.
3. **Auditoria de Qualidade (Heurísticas por Severidade):**
   - 🔴 **Alerta Crítico:** Chave primária duplicada; nulos > 20% em coluna crítica; números guardados como texto com falha de conversão; valores negativos ou datas futuras onde a regra de negócio proíbe; violação lógica (ex.: data de liquidação anterior à data de emissão, taxa > 100%).
   - 🟠 **Aviso:** Nulos entre 5% e 20%; distribuição altamente assimétrica (`média >> mediana`); placeholders ocultos (`-1`, `999999`); categorias duplicadas por erro de caixa ou espaço nas pontas.
   - 🟡 **Observação:** Colunas constantes (1 único valor), colunas candidatas a descarte na camada de BI para economizar memória.
4. **Entrega Obrigatória:**
   - Bloco pronto para colar na **Seção 3.1 do `<DOC_MESTRE_CONTEXTO>`** (Dicionário de Dados e regras de limpeza necessárias na camada de transformação).
   - Bloco `docs/qualidade-<fonte>.md` listando os alertas 🔴/🟠/🟡 e as regras de tratamento recomendadas.
   - Sugestão de 3 a 5 cruzamentos ou verificações de negócio imediatas.
