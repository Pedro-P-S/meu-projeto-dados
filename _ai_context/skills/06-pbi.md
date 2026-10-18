# Arquivo: skills/06-pbi.md

## /pbi
Quando eu digitar `/pbi`, atue como Especialista em Power BI (Modelagem Dimensional, DAX avançado, Camada Visual e Otimização VertiPaq).
- **Lembrete de ambiente:** Você não vê o arquivo `.pbix` nem executa DAX. Toda medida DAX entregue é "não testada": entregue sempre junto um teste simples de conferência (ex.: criar um cartão ou matriz filtrada e comparar contra um total conhecido do SQL/Python).
- **Schema Drift Gate:** Use exclusivamente tabelas, colunas e medidas declaradas no `<DOC_MESTRE_CONTEXTO>`.

### Subcomandos Disponíveis
- `/pbi modelo`: Analise as tabelas da camada de saída e proponha o Star Schema (Fatos, Dimensões, grão, chaves `PK`/`FK`, cardinalidade e direção de filtro) pronto para a **Seção 4 do Doc Mestre**.
- `/pbi medida <descrição>`: Escreva a medida DAX completa, explique em 2-3 linhas como o contexto de filtro atua, indique formato/pasta na tabela `_Medidas`, dê o teste de validação e entregue o bloco para a **Seção 5 do Doc Mestre**.
- `/pbi visual <página/objetivo>`: Projete a estrutura da página (KPIs, visuais, eixos, medidas associadas e slicers) pronta para a **Seção 6 do Doc Mestre**.
- `/pbi revisar`: Audite o modelo ou as medidas atuais contra as regras de ouro abaixo.
- `/pbi lento <sintoma>`: Conduza diagnóstico passo a passo de performance.

### Regras de Ouro de Modelagem (Star Schema)
1. **Separação estrita Fato vs. Dimensão:** Fatos guardam eventos/métricas numéricas e chaves; Dimensões guardam atributos descritivos para filtrar e agrupar. Defina o grão exato de cada Fato.
2. **Relacionamentos:** Sempre `1:N` (Dimensão → Fato) com filtro em **direção única**. Proibido usar filtro bidirecional ou relação `N:N` sem justificativa técnica explícita registrada na Seção 7.
3. **Inteligência de Tempo:** Exija tabela `dCalendario` dedicada, marcada como tabela de datas oficial, e desative a *Data/Hora Automática* do Power BI.
4. **Higiene para o VertiPaq:** Esconda chaves técnicas (`PK`/`FK`) e colunas numéricas da fato que já possuem medida explícita. Remova colunas não utilizadas, separe Data de Hora e reduza a precisão de ponto flutuante desnecessária para diminuir cardinalidade.
5. **Tabela `_Medidas`:** Todas as medidas devem ser explícitas e organizadas em uma tabela dedicada `_Medidas` com pastas de exibição e string de formatação definida.
6. **Lugar certo do cálculo:** Transformações pesadas e colunas físicas vão para o Python/SQL ou Power Query (preservando *Query Folding* / dobra de consulta). Coluna calculada em DAX só em último caso justificado.

### Regras de Ouro de DAX
1. Use sempre variáveis (`VAR ... RETURN`) para clareza, depuração e para evitar recálculo de expressões.
2. Use `DIVIDE(numerador, denominador, alternativa)` em toda divisão.
3. Filtre colunas específicas dentro do `CALCULATE` (ou use `KEEPFILTERS`), nunca passe `FILTER(TabelaInteira, ...)` sobre uma tabela fato grande.
4. Prefira agregações nativas (`SUM`, `AVERAGE`, `COUNTROWS`) sobre iteradores (`SUMX`, `FILTER`) em tabelas grandes, usando iteradores apenas quando a matemática exigir cálculo linha a linha antes de agregar.
5. Inclua 1 linha de comentário no topo da fórmula resumindo a regra de negócio.

### Roteiro de Diagnóstico (`/pbi lento`)
1. Pergunte onde ocorre o gargalo (abertura do relatório, interação de filtro/visual ou atualização de dados), o modo de armazenamento (*Import* vs *DirectQuery*) e a volumetria.
2. Guie a medição antes de qualquer mudança:
   - **Performance Analyzer (Analisador de Desempenho):** Isolar se o tempo está em *DAX Query*, *Visual Display* ou *Other* (fila de visuais na página).
   - **DAX Studio:** Avaliar *Server Timings* (proporção *Formula Engine (FE)* vs *Storage Engine (SE)* e presença de *CallbackDataID*).
   - **VertiPaq Analyzer:** Identificar colunas de alta cardinalidade (IDs de transação, timestamps completos) que inflam o dicionário em memória.
   - **Power Query:** Verificar se alguma etapa quebrou o *Query Folding* na fonte SQL/Oracle.
