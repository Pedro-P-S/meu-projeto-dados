# Conciliação Empréstimo × RAOC × Saldo

Bate **3 fontes** (saldo das contas, base operacional e lançamentos do dia) em **3 medidas** (Empréstimo, RAOC e saldo líquido) e entrega uma lista curta do que arrumar: **qual operação abriu diferença, em qual medida, há quantos dias**.

- Programa: [conciliacao.py](conciliacao.py), arquivo único com testes embutidos
- Regras e desenho: [_ai_context/01-doc-mestre-contexto.md](_ai_context/01-doc-mestre-contexto.md)
- Prompt para o GPT Sol: [docs/prompt-gpt-sol.md](docs/prompt-gpt-sol.md)
- Perguntas em aberto: [docs/perguntas.md](docs/perguntas.md)

## O que sai: aba PENDENCIAS

| Prioridade | Onde | Operação | Conta | Dif. saldo | Dif. Empréstimo | Dif. RAOC | Desde | Idade (dias) |
|---|---|---|---|---|---|---|---|---|
| 1 | Base ≠ Lançamentos | 12345 | 1000099 | −5,00 | 0,00 | 5,00 | 13/11/2026 | 0 |
| 1 | Contábil ≠ Lançamentos | — | 1000002 | 5,00 | 5,00 | 0,00 | 13/11/2026 | 0 |
| 4 | Histórico | — | G1 | 0,00 | 10,00 | 10,00 | até 12/11/2026 | 1 |

**Prioridade:**
- **1:** mexe no saldo líquido.
- **2:** só mexe em Empréstimo ou RAOC.
- **3 e 4:** diferenças antigas, que já estavam na baseline.

**Onde:**
- **Base ≠ Lançamentos:** a operação mexeu na base e o lançamento do dia não veio igual.
- **Contábil ≠ Lançamentos:** a conta mudou no contábil sem lançamento do dia (por exemplo, um lançamento manual).
- **Não explicada:** diferença que nenhum item explica; geralmente um dia não processado.

As linhas de um grupo somam a diferença do grupo, que aparece na aba `RESUMO`. As abas `DET_*` têm o detalhe, para quem precisar.

## Passo a passo no PC do trabalho

1. Crie uma pasta, por exemplo `C:\conciliacao`.
2. No GitHub, abra `conciliacao.py`, clique em **Raw**, `Ctrl+A`, `Ctrl+C`. Cole no Bloco de Notas e salve como `conciliacao.py` na pasta, em **UTF-8**.
3. Teste. Escolha um dos jeitos:
   - **Spyder:** abra o `conciliacao.py` e aperte **Run** (F5). Aparece um menu; digite `1` (autoteste).
   - **Console do Spyder:** `runfile('conciliacao.py', args='autoteste')`
   - **Prompt do Anaconda ou cmd**, na pasta: `python conciliacao.py autoteste`

   (Digitar `python conciliacao.py ...` dentro do console do Spyder dá *syntax error*; esse comando é do terminal.)
   O `resumo_verificacao.txt` tem que terminar com `RESULTADO: TUDO OK`.
4. Rode o exemplo com dados inventados:
   ```
   python conciliacao.py modelo
   python conciliacao.py conciliar 2026-11-12
   python conciliacao.py baseline 2026-11-12
   python conciliacao.py conciliar 2026-11-13
   ```
   Abra `saidas\conciliacao_2026-11-13.xlsx`.
5. Ligue nas fontes reais. Apague `config_local\` e `dados\` do exemplo e rode `python conciliacao.py modelo` de novo. No `config_local\config.xlsx`:
   - Aba `FONTES`: uma linha por fonte, com o SQL ou o caminho do arquivo. Para o CSV de lançamentos de cada dia, use `{aaaammdd}` no nome do arquivo.
   - Conexão com senha: na string de conexão escreva `PWD={senha}`. O programa pergunta a senha ao rodar (não aparece na tela). Para não digitar todo dia, crie a variável de ambiente `CONCILIACAO_SENHA` na sua conta do Windows.
   - Coluna `sistema`: com um sistema de origem só, deixe vazia em todas as linhas.
   - Aba `PARAMETROS`: coloque em `nome_base`, `nome_lancamentos` e `nome_contabil` os nomes que vocês usam.
   - Aba `COLUNAS`: apague as linhas do exemplo e deixe a aba vazia.
6. Deixe o programa achar as colunas:
   ```
   python conciliacao.py descobrir
   ```
   Ele preenche a aba `COLUNAS` sozinho e marca a confiança de cada sugestão. Confira as de confiança média ou baixa. Os nomes e tipos de todas as colunas ficam em `descoberta.xlsx`; ela é só para você, não mande para IA.
7. Preencha a aba `CONTAS` a partir do seu Excel de-para: código da base em `conta_operacional`, contas de Empréstimo e RAOC e o grupo. As contas da aba são a lista do que o programa pega do saldo contábil. Se a conta vem num formato estranho (dentro de um campo longo, espalhada em vários campos ou misturada), rode:
   ```
   python conciliacao.py contas
   ```
   Ele acha a regra que monta a conta, grava no config e diz quantas contas da aba `CONTAS` encontrou (`contas.txt`).
   Depois deixe o programa testar pelos valores as colunas duvidosas:
   ```
   python conciliacao.py hipoteses 2026-11-14
   ```
   O `hipoteses.txt` diz qual candidata fecha melhor. Ele só mostra nomes, sem valores.
8. Comece a rotina:
   ```
   python conciliacao.py conciliar 2026-11-14
   python conciliacao.py baseline 2026-11-14
   ```
   Daí em diante, rode `conciliar` **todo dia útil, em ordem**. Em feriado, use `--anterior AAAA-MM-DD`.

Se der erro, me traga só a última linha do erro, as linhas `FALHOU` do `resumo_verificacao.txt` ou o `hipoteses.txt`.

## O que é público e o que fica só no trabalho

| No GitHub (genérico) | Só no PC do trabalho |
|---|---|
| `conciliacao.py`, documentação | `config_local/` com nomes reais |
| dados de exemplo inventados (gerados pelo `modelo`) | `dados/`, `saidas/`, `historico/`, `descoberta.*`, `hipoteses.*` |

## Proteção do repositório

- Repo público: qualquer um lê, **só o dono escreve**.
- Fork ou pull request de terceiros não muda nada sem você aceitar.
- O branch `main` bloqueia force-push e exclusão.
- Confira que a URL é do seu usuário e que a primeira linha do `resumo_verificacao.txt` mostra a versão esperada.

## Estrutura

```
conciliacao-emprestimo-raoc/
├── conciliacao.py                  programa (arquivo único)
├── README.md
├── .gitignore
├── _ai_context/
│   └── 01-doc-mestre-contexto.md   regras e desenho (fonte da verdade)
└── docs/
    ├── perguntas.md
    └── prompt-gpt-sol.md
```
