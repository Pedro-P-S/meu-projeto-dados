# Perguntas abertas — rodada 2

Rodada 1 respondida e incorporada ao Doc Mestre (arquivo único, foto diária, tolerância 0, faixas de atraso até mais de 3 anos, multa e mora no Empréstimo, publicação no repo).

Responda `sim` para aceitar as recomendações, ou `1 sim, 2 não, 3 <outra>`. Nenhuma resposta precisa de valor real.

1. **Marca de congelada.** A base tem uma coluna que diz se a operação está congelada? Em qual tabela: parcelas ou posição? Recomendo: mapear em `congelada` na tabela onde estiver; o código aceita nas duas.
2. **Juros congelados da pós.** Para a pós congelada, a base tem uma coluna com os juros acumulados desde o congelamento (o que foi a crédito de RAOC)? Se não tiver, existe um "saldo sem congelamento" para eu calcular a diferença? Sem recomendação: preciso saber.
3. **Critério de congelamento.** Congela por dias de atraso (quantos?) ou por estágio de risco? Recomendo: com o critério, eu adiciono um alerta para operação que deveria estar congelada e não está (e vice-versa).
4. **Multa e mora no saldo.** O saldo devedor da posição já inclui multa e mora? Recomendo: deixar `saldo_inclui_multa_mora = sim` e conferir na operação de exemplo. Se a C2 da conta der diferença igual à multa + mora, troca para `nao`.
5. **Atualização do indexador da pós.** A correção de CDI/Selic vai para as mesmas contas que os juros contratuais (D Empréstimo / C Rendas)? Recomendo: sim, mesma regra.
6. **Operação de exemplo.** Escolha uma pós congelada, uma pós normal e uma pré em atraso. Recomendo: olhar as três na aba `OPERACOES` e conferir com o razão contábil delas. Você me diz só "bateu" ou "não bateu" em C1/C2 de cada uma.
