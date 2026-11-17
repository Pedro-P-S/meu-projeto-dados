# Prompt para o GPT Sol (PC do trabalho)

Copie tudo abaixo da linha para o GPT Sol, junto com o `00-rules.md` e o Doc Mestre (`_ai_context/01-doc-mestre-contexto.md`).

---

<TAREFA_ATUAL>
Ticket: preencher o `config_local/config.xlsx` da conciliação Empréstimo × RAOC × Saldo com os nomes reais deste ambiente.

Contexto:
- O programa é o `conciliacao.py` (arquivo único, já testado). **Não altere o `conciliacao.py`.** Se achar um erro nele, descreva o erro e pare.
- O config tem as abas descritas na seção 3.2 do Doc Mestre. O `python conciliacao.py modelo` cria um config de exemplo com dados inventados; use-o como molde.
- Você nunca vê valores dos dados, só nomes e tipos de colunas.

Passos:
1. Peça para eu rodar `python conciliacao.py diagnostico` e colar o `diagnostico.txt` (só nomes e tipos de colunas).
2. Para cada fonte (`saldo_contabil`, `parcelas`, `posicao`, `conciliacao_atual`), monte as linhas da aba `FONTES`:
   - Se a fonte vier do Access ou do Oracle, use `tipo = odbc`, a string de conexão em `caminho_ou_conexao` (sem senha; use a autenticação do Windows ou o DSN que já existe) e o SQL em `aba_ou_consulta`, filtrando a data com `{data_base}` ou `{data_base_br}`.
   - Se for arquivo, `tipo = excel` ou `csv`.
3. Monte a aba `COLUNAS`: para cada coluna canônica da seção 3.1, qual coluna real corresponde. As obrigatórias não podem ficar sem mapa. As opcionais (`multa`, `mora`, `raoc_informado`, `saldo_parcela`, `indexador`, `congelada`, `juros_congelados`) ficam vazias se a coluna não existir.
4. Aba `CONTAS`: me ajude a achar, no Excel/Access da conciliação atual, onde está o par conta Empréstimo → conta RAOC. Escreva um script Python que leia esse de-para e grave a aba `CONTAS`. O script imprime só OK/FALHOU (sem contas nem valores).
5. Aba `INDEXADORES`: liste os valores distintos da coluna de indexador (são códigos, não dados de cliente) e classifique cada um em PRE ou POS.
6. Entregue as linhas de cada aba como tabela para eu colar no Excel, ou um script que grave o config inteiro.
7. Verificação: eu rodo `python conciliacao.py diagnostico` e depois `python conciliacao.py conciliar`, e colo o `resumo_verificacao.txt`. Repita até não haver FALHOU de configuração. FALHOU em "sem diferenças NOVAS" é esperado na primeira rodada.

Critério de pronto: `diagnostico` todo OK e, no `conciliar`, a checagem "C3 = conciliação atual em todos os grupos" OK.
</TAREFA_ATUAL>
