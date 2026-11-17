# Prompt para o GPT Sol (PC do trabalho)

Copie tudo abaixo da linha para o GPT Sol, junto com o `00-rules.md` e o Doc Mestre (`_ai_context/01-doc-mestre-contexto.md`).

---

<TAREFA_ATUAL>
Ticket: ligar o `conciliacao.py` nas fontes reais, preenchendo o `config_local/config.xlsx`.

Regras:
- **Não altere o `conciliacao.py`.** Se achar um erro nele, descreva e pare.
- Você nunca vê valores dos dados. Recebe só nomes de tabelas e colunas, tipos e resultados OK/FALHOU.
- O programa já descobre as colunas sozinho (`descobrir`) e testa as duvidosas pelos valores (`hipoteses`). Seu trabalho é preparar o que ele não consegue fazer sozinho.

Passos:
1. **Aba `FONTES`.** Uma linha por fonte, com `apelido` = `saldo_contabil`, `parcelas`, `posicao`, `lancamentos` ou `conciliacao_atual`.
   - Access/Oracle: `tipo = odbc`. A string de conexão vai em `caminho_ou_conexao`, com `PWD={senha}` no lugar da senha (o programa pergunta ao rodar). Nunca escreva a senha. O SQL vai em `aba_ou_consulta`, filtrando o dia com `{data_base}` (AAAA-MM-DD) ou `{data_base_br}` (DD/MM/AAAA). Use `SELECT *` para o `descobrir` ver todas as colunas.
   - `sistema` = sistema de origem das operações. Com um só, deixe vazio.
   - Arquivo: `tipo = csv` (separador detectado sozinho) ou `excel`. Se houver um arquivo por dia, use `{aaaammdd}` ou `{ddmmaaaa}` no nome.
2. Eu rodo `python conciliacao.py descobrir` e colo o `descoberta.txt` (só nomes de colunas). Revise as sugestões de confiança média ou baixa e as colunas obrigatórias (marcadas com `*`) sem sugestão. Diga qual alternativa usar, ou a fórmula `COL_A + COL_B`.
3. **Aba `CONTAS`.** Ajude a achar, no Excel/Access da conciliação atual, o de-para conta Empréstimo → conta RAOC (e o grupo). Escreva um script Python que leia esse de-para e grave a aba `CONTAS`, imprimindo só OK/FALHOU.
4. **Aba `INDEXADORES`.** Classifique cada código de indexador (a lista está na `descoberta.xlsx`, que eu leio para você) em PRE ou POS.
5. Eu rodo `python conciliacao.py hipoteses AAAA-MM-DD` e colo o `hipoteses.txt`. Ajuste o config para o candidato em 1º lugar de cada hipótese, ou explique por que não.
6. Verificação: eu rodo `conciliar` e colo as linhas `FALHOU` do `resumo_verificacao.txt`. Repita até não haver FALHOU de configuração.

Critério de pronto: `descobrir` sem FALHOU e, no `conciliar`, "C3 = conciliação atual em todos os grupos" OK.
</TAREFA_ATUAL>
