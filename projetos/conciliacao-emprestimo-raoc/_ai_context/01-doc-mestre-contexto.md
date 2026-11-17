# Doc Mestre — Conciliação Empréstimo × RAOC × Saldo

> Segue a estrutura de 8 seções do `00-rules.md` do `meu-projeto-dados`.
> Documento **público**: nada de nomes reais de sistemas, tabelas, colunas, contas ou valores. Os nomes reais ficam só em `config_local/config.xlsx` no PC do trabalho (os nomes de exibição das fontes também: parâmetros `nome_base`, `nome_lancamentos`, `nome_contabil`).

## 1. Visão Geral e Status Atual

- **Versão:** 0.2.6 — `conciliacao.py` (arquivo único). Autoteste 46/46 OK em pandas 1.5, 2.0 e 3.1.
- **Objetivo:** bater **3 fontes** (saldo das contas, base operacional, lançamentos do dia) em **3 medidas** (Empréstimo, RAOC, saldo líquido = Empréstimo − RAOC) e dizer **qual operação abriu diferença, em qual medida, há quantos dias**.
- **Prioridades do negócio:**
  1. **Estancar o sangramento:** achar a operação que abriu diferença hoje, antes de arrumar diferenças antigas.
  2. **Saldo líquido primeiro**, depois Empréstimo e RAOC separados.
  3. Pouca informação para quem vai arrumar: a aba `PENDENCIAS` tem 9 colunas.
- **Próximos passos:**
  1. No trabalho: `autoteste`, `modelo` e o fluxo de exemplo.
  2. Preencher a aba `FONTES` com os nomes reais e rodar `descobrir` (sugere as colunas sozinho).
  3. Rodar `hipoteses` para escolher pelos valores as colunas duvidosas (saldo, juros congelados, código de congelada).
  4. Conciliar um dia, gravar a baseline e, a partir do dia seguinte, rodar todo dia.

## 2. Fontes de Dados e Infraestrutura

| Apelido | O que é | Grão |
|---|---|---|
| `saldo_contabil` | Saldo de cada conta contábil | 1 linha por conta por dia |
| `parcelas` | Parcelas em aberto da base operacional (foto diária) | 1 linha por parcela por dia |
| `posicao` | Posição da operação na base operacional (foto diária) | 1 linha por operação por dia |
| `lancamentos` | Lançamentos do dia que a base operacional mandou para a contabilidade (CSV) | 1 linha por lançamento |
| `conciliacao_atual` | Diferença da conciliação que já existe (validação) | 1 linha por conta |

- **Tipos de leitura:** `excel`, `csv` (separador detectado sozinho: `;` `,` tab ou `|`; ou informe em `aba_ou_consulta`) e `odbc` (Access ou Oracle, SQL na aba `FONTES`).
- **Marcadores de data** em caminho e SQL: `{data_base}` (AAAA-MM-DD), `{data_base_br}` (DD/MM/AAAA), `{aaaammdd}`, `{ddmmaaaa}`. Exemplo: um CSV de lançamentos por dia.
- **Médio prazo:** tirar o Access do meio, com SQL direto no Oracle via `odbc`.
- **Ambiente:** Windows, Python, `pandas` (1.5+), `openpyxl`, `pyodbc` (só para `odbc`).
- **Onde estão os dados:** saldo das contas, parcelas e posição estão no mesmo banco de dados (data warehouse), que recebe dados de vários sistemas. Os lançamentos do dia são um CSV gerado pelo sistema de crédito, um arquivo por dia.
- **Senha:** nunca no config. Na conexão, escreva `PWD={senha}` (ou `{senha:NOME}` para mais de um banco). O programa lê a variável de ambiente `CONCILIACAO_SENHA` (ou `CONCILIACAO_SENHA_NOME`); se ela não existir, pergunta uma vez por execução: no terminal sem mostrar o texto; no Spyder numa janela com ****, fora do histórico do console.
- **`sistema` (FONTES/COLUNAS):** é o sistema de origem, dono do número da operação, não o banco de onde a tabela vem. Com um sistema só, deixe vazio em tudo. Com vários: filtre cada sistema no SQL, preencha `sistema` nas linhas de parcelas, posição e lançamentos daquele sistema, e só casam lançamento e operação do mesmo sistema. Lançamento sem `sistema`, com um só sistema na base, é atribuído a ele.

### Extensibilidade

- **Conta nova:** uma linha em `CONTAS`.
- **Base de outro sistema:** linhas em `FONTES` e `COLUNAS` com outro `sistema`. A chave de operação é (sistema, operação).
- **Indexador novo:** uma linha em `INDEXADORES`.
- **Faixa de atraso nova:** uma linha em `FAIXAS_ATRASO`.
- **Coluna que é soma de outras:** em `coluna_origem`, escreva `COL_A + COL_B - COL_C` (com espaço em volta do sinal).

## 3. Dicionário de Dados e Esquema

### 3.1 Modelo canônico (obrigatórias em negrito)

- **`saldo_contabil`**: **conta**, **saldo**, data_base.
- **`parcelas`**: **operacao**, **num_parcela**, **conta_operacional**, **vencimento**, **valor_vencimento**, data_base, multa, mora, raoc_informado, saldo_parcela, indexador, congelada, juros_congelados.
- **`posicao`**: **operacao**, **conta_operacional**, **saldo_devedor**, data_base, indexador, congelada, juros_congelados, multa, mora.
- **`lancamentos`**: **conta**, **valor**, data_base, natureza (D/C; vazia = valor já com sinal, devedor positivo), operacao, historico.
- **`conciliacao_atual`**: **conta**, **diferenca**, data_base.

Conversões:
- **Números:** aceita vírgula decimal; número vazio vira 0 nas colunas opcionais.
- **Datas:** DD/MM/AAAA ou AAAA-MM-DD.
- **Conta:** perde a pontuação.
- **Operação:** perde os zeros à esquerda.
- **Congelada:** a operação conta como congelada quando o valor da coluna `congelada` está em `valores_congelada`.

### 3.2 Config (`config_local/config.xlsx`)

| Aba | Colunas |
|---|---|
| `PARAMETROS` | `nome`, `valor` (ver lista abaixo) |
| `FONTES` | `apelido`, `sistema`, `tipo`, `caminho_ou_conexao`, `aba_ou_consulta` |
| `COLUNAS` | `apelido`, `sistema`, `coluna_canonica`, `coluna_origem` (+ `sugerido`, `alternativas` escritas pelo `descobrir`) |
| `CONTAS` | `conta_operacional`, `conta_emprestimo`, `conta_raoc`, `grupo`, `sinal_emprestimo`, `sinal_raoc`, `ativa` |
| `INDEXADORES` | `valor_origem`, `tipo` (PRE/POS) |
| `FAIXAS_ATRASO` | `faixa`, `de_dias`, `ate_dias` |

Parâmetros:

| Parâmetro | Padrão |
|---|---|
| `data_base` | |
| `data_base_anterior` | vazio = dia útil anterior |
| `tolerancia_conta`, `tolerancia_operacao` | 0 |
| `fonte_saldo_devedor` | `posicao` |
| `saldo_inclui_multa_mora` | `sim` |
| `indexador_padrao` | `PRE` |
| `valores_congelada` | `S,SIM,1,TRUE,CONGELADA` |
| `sinal_conciliacao_atual` | 1 |
| `nome_base`, `nome_lancamentos`, `nome_contabil` | |
| `pasta_saidas` | `saidas` |
| `pasta_historico` | `historico` |

### 3.3 Contratos de funções (`conciliacao.py`)

- `carregar_fontes(cfg, P, data_base, raiz, v, cache, apelidos) -> dict[str, DataFrame]`: modelo canônico por apelido.
- `calcular_operacoes(dados, contas, indexadores, faixas, P, data_base, v) -> DataFrame`: 1 linha por (sistema, operação).
- `conciliar_contas(ops, contabil, contas, v) -> (DataFrame, list)`: C1, C2, C2b, C3 por conta/grupo.
- `conciliar_movimento(res_d, res_a, ops_d, ops_a, lanc, contas, P, v) -> (mov_contas, mov_ops, itens)`: movimento do dia.
- `montar_pendencias(db, res, contas, pasta_hist, P, varios_sistemas, v, itens) -> (pend, residuos, data_baseline)`.
- `sugerir_mapa(amostra, apelido) -> (escolhido, alternativas, tipos)`: descoberta por nome e tipo.
- `hipoteses(config, data_base) -> (melhores, tabela)`: escolha pelos valores.

## 4. Modelagem e Relacionamentos

- `parcelas` N:1 `posicao` por (sistema, operação); junção externa, e a sobra vira alerta.
- `conta_operacional` N:1 `CONTAS`. Uma conta RAOC pode servir várias contas Empréstimo, no mesmo grupo.
- `lancamentos.conta` é a conta contábil. Só contam lançamentos em contas Empréstimo ou RAOC da aba `CONTAS`.
- **Fluxo diário:**
  1. Fontes do dia D e do dia anterior → modelo canônico.
  2. Estoque por conta (contábil − base) nos dois dias.
  3. Movimento: Δ contábil, Δ base e lançamentos, por conta e por (operação, conta).
  4. Itens divergentes do dia vão para o histórico.
  5. Pendências abertas (itens acumulados ≠ 0) + baseline + resíduo → Excel.

## 5. Métricas, Cálculos e Regras de Negócio

### 5.1 Por operação

`saldo_op` = `saldo_devedor` (+ multa + mora se `saldo_inclui_multa_mora = nao`). Multa e mora podem vir das parcelas ou da posição (soma das duas; mapeie em uma só).

| Regra | `emprestimo_op` | `raoc_implicito` |
|---|---|---|
| PRE | Σ valor_vencimento + multa + mora | emprestimo_op − saldo_op |
| PRE congelada | igual | igual (o saldo da base para e o RAOC cresce junto) |
| POS | saldo_op | 0 (juros e correção: D Empréstimo / C Rendas) |
| POS congelada | saldo_op + juros_congelados | juros_congelados (D Empréstimo / C RAOC) — **provisória** |

### 5.2 Estoque por conta (dia D)

| | Fórmula | Nível |
|---|---|---|
| C1 | contábil(Empréstimo) − Σ emprestimo_op | conta Empréstimo |
| C2 | contábil(RAOC) − Σ raoc_implicito | conta RAOC |
| C2b | contábil(RAOC) − Σ raoc_coluna | conta RAOC |
| C3 | Σ contábil(Emp) − Σ contábil(RAOC) − Σ saldo_op | grupo |

### 5.3 Movimento do dia (D − dia anterior)

Lançamentos com sinal natural da conta: Empréstimo `D − C`; RAOC `C − D`.

- **Contábil ≠ Lançamentos (por conta):** `Δ contábil − lançamentos`. Mostra lançamento fora do arquivo do dia, por exemplo um manual.
- **Base ≠ Lançamentos (por operação e conta):** `Δ base − lançamentos`. Mostra a operação que mexeu na base sem o lançamento igual: faltou, sobrou ou foi para outra conta.
- **Base ≠ Lançamentos (sem operação):** a parte da conta que nenhuma operação explica, por exemplo um lançamento sem número de operação.
- **Identidade:** Δ(contábil − base) = (Δ contábil − lanç.) − (Δ base − lanç.). Assim, toda mudança na diferença de uma conta vira um item com dono.

### 5.4 Pendências e idade

- **Impacto** de um item = quanto ele muda a diferença contábil − base da conta (Contábil ≠ Lanç. entra com +, Base ≠ Lanç. entra com −).
- O histórico guarda os itens de cada dia. Uma pendência fica **aberta** enquanto o acumulado dela (por tipo, operação e conta) for diferente de 0. **Desde** = dia em que o acumulado deixou de ser 0.
- **Histórico:** as diferenças C1 e C2 da baseline. **Não explicada:** diferença − baseline − Σ itens; a idade conta os dias seguidos de execução em que ela aparece.
- Por construção, **Σ pendências de um grupo = diferença contábil − base do grupo**.
- **Prioridade:**

| Prioridade | Quando |
|---|---|
| 1 | Não é histórico e mexe no saldo líquido |
| 2 | Não é histórico e só mexe em Empréstimo/RAOC |
| 3 | Histórico que mexe no saldo |
| 4 | Histórico que não mexe no saldo |

- **Ordem dentro da prioridade:** idade crescente, depois maior valor.
- **Rodar o mesmo dia de novo substitui** os itens daquele dia (não duplica).
- **Histórico contínuo:** se o dia anterior não foi conciliado, a checagem avisa e a diferença do dia que faltou aparece como "não explicada".

### 5.5 Descoberta e hipóteses

- **`descobrir`:** lê uma amostra de cada fonte e pontua cada coluna para cada campo canônico. A pontuação usa palavras do nome e o tipo detectado (data, número, texto). Grava a melhor sugestão na aba `COLUNAS`, só onde estava vazio, com confiança e alternativas. Faz backup do config.
- **`hipoteses`:** roda o estoque com cada candidato e ordena pela soma de |diferença| de C1, C2 e C3. Candidatos testados:
  - colunas `SALDO*` da posição, para o saldo devedor;
  - colunas `*CONG*`, sozinhas e somadas, com e sem as `DESCONG`, para os juros congelados;
  - cada código distinto da coluna `congelada`, para `valores_congelada`;
  - `saldo_inclui_multa_mora` sim e não.

  O `hipoteses.txt` só tem nomes e posições no ranking.

## 6. Saídas

`saidas/conciliacao_<data>.xlsx`, abas nesta ordem:

| Aba | Conteúdo |
|---|---|
| `PENDENCIAS` | **Prioridade, Onde, Operação, Conta, Dif. saldo, Dif. Empréstimo, Dif. RAOC, Desde, Idade (dias)**, com cor por prioridade |
| `RESUMO` | 1 linha por grupo: diferenças das 3 medidas, pendências abertas, abertas hoje, não explicada |
| `DET_CONTAS` | C1, C2, C2b, C3 por conta/grupo |
| `DET_MOVIMENTO_CONTAS` | Δ contábil, Δ base e lançamentos por conta |
| `DET_MOVIMENTO_OPERACOES` | operação × conta com divergência no dia |
| `DET_OPERACOES` | cálculo completo por operação |
| `DET_ATRASO` | Σ por grupo, conta, faixa de atraso e congelada |
| `DET_INCONSISTENCIAS` | alertas de dados |
| `DET_VALIDACAO_ATUAL` | C3 × conciliação atual |
| `LEGENDA_PARAMETROS` | legenda das colunas e dos tipos de "Onde", parâmetros, linhas lidas |

`historico/`: `baseline.xlsx`, `itens.csv`, `residuos.csv`, `execucoes.csv`. Só ficam no PC do trabalho.

## 7. Decisões, Rotas Descartadas e Pendências

### Decisões ativas
- **ADR-001 — RAOC implícito:** a coluna de RAOC da base está errada. O RAOC vem de Empréstimo − saldo; a coluna só mede o erro (C2b).
- **ADR-002 — Modelo canônico + config:** contas, sistemas, indexadores e faixas novos entram pelo config.
- **ADR-003 — Repo público genérico:** nomes reais e nomes de exibição só em `config_local/`.
- **ADR-004 — Arquivo único** com autoteste, para copiar pelo navegador.
- **ADR-005 — Multa e mora no Empréstimo**, somadas à parte do valor no vencimento.
- **ADR-006 — Lançamentos do dia como fonte de identificação:** a diferença nova é atribuída à operação comparando o Δ base com os lançamentos por (operação, conta). O contábil é comparado com os lançamentos por conta.
- **ADR-007 — Pendência com impacto aditivo:** toda pendência é medida no mesmo sinal (contábil − base). Por isso a lista soma a diferença do grupo e o resíduo mostra o que falta explicar.

### Rotas descartadas
- **Conciliar só o líquido:** esconde erros que se anulam.
- **Status OK/CONHECIDA/MUDOU/NOVA (v0.1):** trocado por pendências com idade, que apontam a operação.
- **Um Excel por conta; GPT Sol escrevendo o código.**
- **Alerta de "deveria estar congelada":** o critério vem de outro sistema (90+ dias e outros casos); não compensa.

### Pendências
- Validar com uma operação de exemplo a regra da POS congelada e quais colunas `*CONG*` entram (o `hipoteses` sugere).
- Montar a aba `CONTAS` a partir do Excel/Access da conciliação atual.
- Migrar a lógica do Access para SQL no Oracle.

## 8. Glossário

- **Base**: as tabelas de parcelas e posição no banco de dados. No relatório, recebe o nome de `nome_base`. _Evitar_: o nome interno do banco (no repo público).
- **Sistema de origem**: sistema que manda as operações para o banco de dados. É o dono do número da operação.
- **Lançamentos do dia**: arquivo com todos os lançamentos contábeis que a base mandou no dia. _Evitar_: o nome interno do arquivo.
- **Conta Empréstimo**: guarda parcelas no vencimento + multa + mora (PRE) ou saldo atualizado (POS).
- **RAOC**: Rendas a Apropriar de Operações de Crédito, conta retificadora.
- **Saldo líquido**: Empréstimo − RAOC. É a medida prioritária.
- **RAOC implícito**: Empréstimo da base − saldo devedor, por operação.
- **Operação congelada**: operação cujos juros vão a crédito de RAOC em vez de rendas.
- **Pendência**: item que explica parte da diferença contábil − base, com dono (operação ou conta) e idade.
- **Baseline**: foto das diferenças antigas; aparecem como "Histórico".
- **Não explicada**: parte da diferença que nenhuma pendência explica.
- **Grupo**: contas Empréstimo e RAOC que fecham juntas no saldo líquido.
