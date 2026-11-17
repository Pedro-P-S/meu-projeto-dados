# Doc Mestre — Conciliação Empréstimo × RAOC × Saldo

> Segue a estrutura de 8 seções do `00-rules.md` do `meu-projeto-dados`.
> Documento **público**: nada de nomes reais de tabelas, colunas, schemas, servidores, contas ou valores. Os nomes reais ficam só em `config_local/config.xlsx` no PC do trabalho.

## 1. Visão Geral e Status Atual

- **Versão:** 0.1.0 — `conciliacao.py` (arquivo único) escrito e testado com dados inventados: autoteste 23/23 OK em pandas 1.5, 2.0 e 3.1.
- **Objetivo:** conciliar, por conta contábil e numa data-base, Empréstimo, RAOC e saldo líquido separadamente, em vez de só o líquido.
- **Por que:** a conciliação atual só olha Empréstimo − RAOC. Erros iguais nos dois lados se anulam e ficam invisíveis.
- **Próximos passos:**
  1. No trabalho: copiar `conciliacao.py`, rodar `autoteste` e `modelo`.
  2. Com o GPT Sol: preencher `config_local/config.xlsx` com os nomes reais e rodar `diagnostico` até tudo OK.
  3. Rodar `conciliar` e conferir que a C3 bate com a conciliação atual.
  4. Gravar a baseline do último fechamento diário.
  5. Validar as regras de pós-fixada e congelada com uma operação de exemplo.

## 2. Fontes de Dados e Infraestrutura

Nomes genéricos. O nome real de cada fonte fica na aba `FONTES` do config.

| Apelido | O que é | Grão | Origem |
|---|---|---|---|
| `saldo_contabil` | Saldo por conta contábil | 1 linha por conta por dia | Oracle |
| `parcelas` | Parcelas em aberto da base operacional | 1 linha por parcela por dia (tem foto diária) | Oracle |
| `posicao` | Posição diária por operação | 1 linha por operação por dia | Oracle |
| `conciliacao_atual` | Diferença da conciliação que já existe | 1 linha por conta | Excel/Access atual (validação) |

- **Leitura:** tipos `excel`, `csv` (separador `;`) e `odbc` (Access ou Oracle, com SQL na aba `FONTES`; aceita `{data_base}` = AAAA-MM-DD e `{data_base_br}` = DD/MM/AAAA).
- **Objetivo de médio prazo:** tirar o Access do meio. Primeiro lê pelo Access que existe; depois a lógica dele migra para SQL direto no Oracle via `odbc`.
- **Ambiente:** Windows, Python, `pandas` (1.5+), `openpyxl`, `pyodbc` (só se usar `odbc`). Credenciais nunca no código nem no repo.

### Extensibilidade

- **Conta nova:** uma linha na aba `CONTAS`.
- **Base de outro sistema:** uma linha em `FONTES` + mapeamento em `COLUNAS`, com outro valor em `sistema`. A chave de operação é (sistema, operação).
- **Indexador novo:** uma linha em `INDEXADORES`.
- **Faixa de atraso nova:** linha em `FAIXAS_ATRASO`.

## 3. Dicionário de Dados e Esquema

### 3.1 Modelo canônico

**`saldo_contabil`**: `data_base` (data, opc), `conta` (texto, sem pontuação), `saldo` (num, sinal de origem; vira positivo pelo sinal da aba `CONTAS`).

**`parcelas`**: `operacao`, `num_parcela`, `conta_operacional`, `vencimento`, `valor_vencimento` (obrigatórias); `data_base`, `multa`, `mora`, `raoc_informado`, `saldo_parcela`, `indexador`, `congelada` (opcionais; número vazio = 0).

**`posicao`**: `operacao`, `conta_operacional`, `saldo_devedor` (obrigatórias); `data_base`, `indexador`, `congelada`, `juros_congelados` (opcionais).

**`conciliacao_atual`**: `conta`, `diferenca` (obrigatórias); `data_base` (opc).

Conversões: texto com vírgula decimal vira número; datas DD/MM/AAAA ou AAAA-MM-DD; `congelada` aceita S/SIM/1/TRUE.

### 3.2 Config (`config_local/config.xlsx`)

| Aba | Colunas |
|---|---|
| `PARAMETROS` | `nome`, `valor` — `data_base`, `tolerancia_conta` (0), `tolerancia_operacao` (0), `fonte_saldo_devedor` (`posicao`), `saldo_inclui_multa_mora` (`sim`), `indexador_padrao` (`PRE`), `sinal_conciliacao_atual` (1), `pasta_saidas`, `arquivo_baseline` |
| `FONTES` | `apelido`, `sistema`, `tipo`, `caminho_ou_conexao`, `aba_ou_consulta` |
| `COLUNAS` | `apelido`, `sistema`, `coluna_canonica`, `coluna_origem` |
| `CONTAS` | `conta_operacional`, `conta_emprestimo`, `conta_raoc`, `grupo`, `sinal_emprestimo`, `sinal_raoc`, `ativa` |
| `INDEXADORES` | `valor_origem`, `tipo` (PRE/POS) |
| `FAIXAS_ATRASO` | `faixa`, `de_dias`, `ate_dias` |

### 3.3 Contratos de funções (`conciliacao.py`)

- `ler_config(caminho) -> (dict[str, DataFrame], dict)` | Entrada: config.xlsx | Saída: abas + parâmetros
- `carregar_fontes(cfg, P, data_base, raiz, v) -> dict[str, DataFrame]` | Saída: modelo canônico por apelido
- `calcular_operacoes(dados, contas, indexadores, faixas, P, data_base, v) -> DataFrame` | Saída: 1 linha por (sistema, operação)
- `conciliar_contas(ops, contabil, contas, v) -> (DataFrame, list)` | Saída: 1 linha por (checagem, conta/grupo)
- `aplicar_baseline(res, baseline, tol) -> DataFrame` | Saída: RESUMO com status
- `executar_conciliacao(config, data_base, v) -> (Path, DataFrame, DataFrame, Verificacao)`

## 4. Modelagem e Relacionamentos

- `parcelas` N:1 `posicao` por (sistema, operação), junção externa: sobra de qualquer lado vira alerta.
- `conta_operacional` N:1 `CONTAS`. `conta_emprestimo` e `conta_raoc` N:1 `saldo_contabil.conta`.
- Uma conta RAOC pode servir várias contas Empréstimo (N:1), dentro do mesmo grupo.
- **Fluxo:** fontes → adaptador (renomeia, converte, filtra data-base) → modelo canônico → cálculo por operação → soma por conta/grupo → contábil → status contra baseline → Excel + `resumo_verificacao.txt`.

## 5. Métricas, Cálculos e Regras de Negócio

### 5.1 Por operação

`saldo_op` = `saldo_devedor` da posição (+ multa + mora se `saldo_inclui_multa_mora = nao`).

| Regra | `emprestimo_op` | `raoc_implicito` |
|---|---|---|
| PRE | Σ `valor_vencimento` + Σ `multa` + Σ `mora` | `emprestimo_op − saldo_op` |
| PRE congelada | igual à PRE | igual à PRE (o saldo da base para de crescer, o RAOC implícito cresce junto) |
| POS | `saldo_op` | 0 (juros vão a D Empréstimo / C Rendas) |
| POS congelada | `saldo_op + juros_congelados` | `juros_congelados` (juros vão a D Empréstimo / C RAOC) — **provisória** |

- `raoc_coluna` = Σ `raoc_informado`; `erro_coluna_raoc` = `raoc_coluna − raoc_implicito`.
- `dif_saldo_cruzado` = Σ `saldo_parcela` − `saldo_devedor` (checagem cruzada).
- `dias_atraso` = data-base − vencimento mais antigo em aberto já vencido (0 se nenhum). Parcelas vencidas ficam na mesma conta.
- Faixas padrão: Em dia, 1-60, 61-90, 91-180, 181-360, 361-3 anos, Mais de 3 anos.

### 5.2 Por conta

| Checagem | Fórmula | Nível |
|---|---|---|
| C1 | `contábil(Empréstimo) − Σ emprestimo_op` | conta Empréstimo |
| C2 | `contábil(RAOC) − Σ raoc_implicito` | conta RAOC |
| C2b | `contábil(RAOC) − Σ raoc_coluna` | conta RAOC |
| C3 | `[Σ contábil(Emp) − Σ contábil(RAOC)] − Σ saldo_op` | grupo |

- Identidade checada: C3 = ΣC1 − ΣC2 no grupo (consistência interna).
- Prova independente: C3 = `conciliacao_atual` por grupo.
- Contas contábeis fora da aba `CONTAS` são ignoradas.

### 5.3 Status

`tol` = `tolerancia_conta` (0 por enquanto; diferenças arredondadas em centavos).

| Status | Regra |
|---|---|
| OK | `abs(dif) ≤ tol` |
| CONHECIDA | há baseline acima de `tol` e `abs(dif − baseline) ≤ tol` |
| MUDOU | há baseline acima de `tol` e `abs(dif − baseline) > tol` |
| NOVA | não há baseline (ou era ≤ `tol`) e `abs(dif) > tol` |

Baseline: `python conciliacao.py baseline AAAA-MM-DD` fotografa as diferenças não zeradas daquela data, mantém os motivos já escritos e guarda cópia da anterior.

## 6. Saídas

`saidas/conciliacao_<data>.xlsx`:

| Aba | Conteúdo |
|---|---|
| `RESUMO` | 1 linha por (checagem, conta/grupo), ordenada por status e tamanho da diferença, com cor por status |
| `OPERACOES` | 1 linha por operação com todos os cálculos da 5.1 e alertas |
| `ATRASO` | Σ por grupo, conta, faixa de atraso e congelada |
| `INCONSISTENCIAS` | operação só em parcelas/só na posição, conta divergente, sem mapa, indexador desconhecido, RAOC negativo, saldo cruzado, conta sem saldo contábil |
| `VALIDACAO_ATUAL` | C3 × conciliação atual por grupo |
| `PARAMETROS` | versão, data-base, parâmetros, linhas lidas, legenda das checagens |

Mais `resumo_verificacao.txt` (só OK/FALHOU) e, no `diagnostico`, `diagnostico.txt` (só nomes e tipos de colunas).

## 7. Decisões, Rotas Descartadas e Pendências

### Decisões ativas
- **ADR-001 — RAOC implícito em vez da coluna:** a coluna de RAOC por parcela da base está errada. O RAOC vem de Empréstimo da base − saldo devedor; a coluna só mede o erro (C2b).
- **ADR-002 — Modelo canônico + config:** contas, sistemas, indexadores e faixas novos entram pelo config, sem mexer no código.
- **ADR-003 — Repo público genérico:** nomes reais só em `config_local/`, nunca no git.
- **ADR-004 — Arquivo único:** `conciliacao.py` é um arquivo só, para copiar do navegador para o PC do trabalho. Testes embutidos (`autoteste`).
- **ADR-005 — Multa e mora no Empréstimo:** entram na conta Empréstimo e não estão no valor no vencimento, por isso são somadas à parte.

### Rotas descartadas
- **Conciliar só o líquido:** esconde erros que se anulam.
- **Um Excel por conta:** ~100 arquivos; trocado por um Excel com filtro.
- **GPT Sol escrever o código:** troca por código testado aqui; o GPT Sol só preenche o config e diagnostica.

### Pendências
- Confirmar com colega e com uma operação de exemplo: regra da POS congelada e de onde vêm `congelada` e `juros_congelados`.
- Confirmar se o saldo devedor da posição já inclui multa e mora (`saldo_inclui_multa_mora`).
- Montar a aba `CONTAS` a partir do Excel/Access da conciliação atual.
- Migrar a lógica do Access para SQL no Oracle.

## 8. Glossário

- **Base operacional**: o sistema de crédito que alimenta o banco de dados com operações e parcelas. _Evitar_: o nome interno do sistema (no repo público).
- **Conta Empréstimo**: conta que guarda as parcelas no vencimento + multa + mora (PRE) ou o saldo atualizado (POS).
- **RAOC**: Rendas a Apropriar de Operações de Crédito, conta retificadora com os juros ainda não reconhecidos.
- **Saldo líquido**: Empréstimo − RAOC.
- **RAOC implícito**: Empréstimo da base − saldo devedor, por operação.
- **RAOC coluna**: soma da coluna de RAOC por parcela da base. Sabidamente errada.
- **Operação congelada**: operação cujos juros passam a ir a crédito de RAOC em vez de rendas, para o saldo líquido não crescer. A base acompanha.
- **Data-base**: data de corte; contábil e base da mesma data.
- **Baseline**: foto das diferenças conhecidas numa data-base. _Evitar_: "histórico".
- **Grupo**: conjunto de contas Empréstimo e RAOC que fecham juntas no saldo líquido.
