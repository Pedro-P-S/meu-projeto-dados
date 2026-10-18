# Arquivo: skills/02-arquitetura.md

## /arquitetura
Quando eu digitar `/arquitetura`, desenhe ou revise a arquitetura técnica do projeto com base no `<DOC_MESTRE_CONTEXTO>`.

### O que entregar
1. **Fluxo de Dados em Camadas (Ponta a Ponta):**
   - `Fonte Bruta` → `Ingestão (leitura e validação de schema)` → `Transformação (limpeza e regras de negócio em Python/SQL)` → `Camada de Saída (Fatos e Dimensões em Parquet/Banco)` → `Consumo BI (Power BI / Relatórios)`.
2. **Árvore de Diretórios e Módulos:**
   - Proponha uma estrutura de pastas enxuta onde cada arquivo Python tenha responsabilidade única.
   - Respeite a diretriz *Simplicity First* (1.2): proibido criar frameworks caseiros, classes abstratas desnecessárias ou camadas que o projeto não precisa hoje.
3. **Contratos entre Módulos (Formato Seção 3.2 do Doc Mestre):**
   - Defina para cada módulo: caminho do arquivo, assinatura da função principal com *type hints*, schema/colunas de entrada esperadas e artefato/schema de saída.
4. **Modelo Dimensional para o BI (Formato Seção 4 do Doc Mestre):**
   - Tabelas Fato e Dimensão que compõem a camada de saída, grão exato de cada uma, chaves (`PK`/`FK`) e cardinalidade.
5. **Infraestrutura, Segredos e Verificabilidade:**
   - Variáveis de ambiente necessárias (apenas nomes, sem valores fixos em código), estratégia mínima de logging e quais testes automatizados (`pytest`) protegem os contratos de borda.
6. **Tradeoffs Arquiteturais:**
   - Apresente pelo menos 2 alternativas viáveis de implementação (ex.: processar em memória com Pandas/Polars vs. empurrar transformação para SQL no banco), compare os tradeoffs e declare a sua recomendação.

### Formato de Saída
Entregue o rascunho pronto para colar nas **Seções 2, 3.2 e 4** do `<DOC_MESTRE_CONTEXTO>`, marcando explicitamente como `[NÃO VERIFICADO]` qualquer ponto que dependa de confirmação nas fontes reais.
