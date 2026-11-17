# Conciliação Empréstimo × RAOC × Saldo

Concilia, por conta contábil, a conta **Empréstimo**, a conta **RAOC** e o **saldo líquido** contra a base operacional de crédito. Hoje só o líquido (Empréstimo − RAOC) é conciliado, e erros que se anulam ficam invisíveis.

- Programa: [conciliacao.py](conciliacao.py), arquivo único com testes embutidos
- Regras e desenho: [_ai_context/01-doc-mestre-contexto.md](_ai_context/01-doc-mestre-contexto.md)
- Prompt para o GPT Sol preencher o config: [docs/prompt-gpt-sol.md](docs/prompt-gpt-sol.md)
- Perguntas em aberto: [docs/perguntas.md](docs/perguntas.md)

## As checagens, por conta

| | Compara | Mostra |
|---|---|---|
| C1 | Empréstimo contábil × (Σ parcelas no vencimento + multa + mora) | erro no lado do Empréstimo |
| C2 | RAOC contábil × RAOC implícito (Empréstimo da base − saldo devedor) | erro no lado do RAOC |
| C2b | RAOC contábil × coluna de RAOC da base | tamanho do erro da coluna |
| C3 | Saldo líquido contábil × saldo devedor da base | o que a conciliação atual já faz |

Cada diferença sai como **OK**, **CONHECIDA** (igual à foto guardada), **MUDOU** ou **NOVA**.

## Passo a passo no PC do trabalho

1. Crie uma pasta, por exemplo `C:\conciliacao`.
2. No GitHub, abra `conciliacao.py`, clique em **Raw**, `Ctrl+A`, `Ctrl+C`. Cole no Bloco de Notas e salve como `conciliacao.py` dentro da pasta, com codificação **UTF-8**.
3. Abra o terminal na pasta e rode:
   ```
   python conciliacao.py autoteste
   ```
   Tem que terminar com `RESULTADO: TUDO OK` no `resumo_verificacao.txt`.
4. Crie o config de exemplo e rode com os dados inventados:
   ```
   python conciliacao.py modelo
   python conciliacao.py conciliar
   ```
   Abra `saidas\conciliacao_2026-10-31.xlsx` para ver como fica.
5. Com o GPT Sol ([docs/prompt-gpt-sol.md](docs/prompt-gpt-sol.md)), troque o exemplo pelos nomes reais no `config_local\config.xlsx`. Confira com:
   ```
   python conciliacao.py diagnostico
   ```
6. Rode a data real e grave a foto das diferenças que já existem:
   ```
   python conciliacao.py conciliar 2026-11-14
   python conciliacao.py baseline 2026-11-14
   ```
   Daí em diante, cada `conciliar` marca o que é NOVA ou MUDOU.

Se der erro, me traga só a última linha do erro ou as linhas `FALHOU` do `resumo_verificacao.txt`.

## O que é público e o que fica só no trabalho

| No GitHub (genérico) | Só no PC do trabalho |
|---|---|
| `conciliacao.py`, documentação | `config_local/` com nomes reais de tabelas, colunas e contas |
| dados de exemplo inventados (gerados pelo `modelo`) | `dados/`, `saidas/`, `baseline/` |

## Proteção do repositório

- Repo público: qualquer um lê, **só o dono escreve** (não há outros colaboradores).
- Fork ou pull request de terceiros não muda nada sem você aceitar.
- O branch `main` bloqueia force-push e exclusão.
- No PC do trabalho não precisa logar no GitHub. Confira que a URL é do seu usuário, não de um fork, e que a primeira linha do `resumo_verificacao.txt` mostra a versão esperada.

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
