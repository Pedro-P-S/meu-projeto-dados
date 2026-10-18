# Arquivo: skills/09-docs.md

## /docs
Quando eu digitar `/docs` (ou `/docs novo`, `/docs atualizar`, `/docs revisar`), gere ou atualize a documentação do repositório em Markdown a partir do `<DOC_MESTRE_CONTEXTO>`.

### Regras Fundamentais
1. **Fonte Única da Verdade:** O `01-doc-mestre-contexto.md` continua sendo a referência técnica central. Não duplique dicionários gigantes no `README.md`; aponte para o documento mestre ou gere os arquivos específicos abaixo.
2. **Zero Invenção:** Tudo o que não constar no `<DOC_MESTRE_CONTEXTO>` deve ficar marcado explicitamente como `_a preencher_`.
3. **Brevidade:** Um bom `README.md` cabe em uma tela e meia. Qualquer desenvolvedor ou analista novo deve entender o objetivo, como configurar o ambiente, como rodar o pipeline e onde estão os dados em 2 minutos de leitura.

### Arquivos a Entregar (cada um em seu bloco markdown com o caminho no topo)

1. **`README.md`:**
   - Título e resumo de 1 frase (o que é e quem consome).
   - Objetivo de negócio (2-3 linhas).
   - Como configurar e rodar (versão do Python, variáveis de ambiente necessárias sem segredos, comandos de execução e de testes `pytest`).
   - Estrutura de pastas (1 linha por diretório/módulo principal).
   - Resumo das fontes de dados e camada de saída.
   - Links para `01-doc-mestre-contexto.md`, `docs/glossario.md` e `docs/decisoes/`.

2. **`docs/glossario.md`:**
   - Apenas termos específicos do negócio/domínio (conceitos gerais de Python/BI não entram).
   - Um termo oficial por conceito, definição de 1 a 2 frases focada no que *é* (sem detalhe de código) e linha `_Evite_: sinônimo1, sinônimo2`.

3. **`docs/decisoes/NNNN-titulo-curto.md` (ADRs — Architecture Decision Records):**
   - Gere apenas para decisões da Seção 7 que cumpram simultaneamente as **3 condições**: (1) difícil de reverter, (2) surpreendente para quem chega sem contexto, e (3) fruto de um tradeoff real entre alternativas.
   - Formato enxuto: Título + 1 parágrafo curto (Contexto, Decisão tomada, Alternativa descartada e Consequência).

Ao final, liste quais pontos ficaram como `_a preencher_`.
