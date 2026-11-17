# Perguntas abertas — rodada 3

As rodadas 1 e 2 já estão no Doc Mestre: lançamentos do dia como 3ª fonte, prioridade do saldo líquido, pendências com idade, congelada pelo código de situação, POS com correção igual aos juros.

Responda `sim` para aceitar as recomendações, ou `1 sim, 2 não, 3 <outra>`. Nenhuma resposta precisa de valor real.

1. **Operação no arquivo de lançamentos.** Cada linha do arquivo de lançamentos traz o número da operação? Recomendo: sim, e é isso que aponta a operação. Se não trouxer, o programa só consegue apontar a conta.
2. **Data no arquivo de lançamentos.** É um CSV por dia (data no nome do arquivo) ou um arquivo com uma coluna de data? Recomendo: um por dia, com `{aaaammdd}` no caminho.
3. **Dia anterior.** O "dia anterior" é sempre o dia útil anterior, ou a base tem foto também em fim de semana e feriado? Recomendo: dia útil anterior, e `--anterior` em feriado.
4. **Baseline.** Recomendo: tirar a baseline no primeiro dia que rodar com dados reais. Tudo que já existe vira "Histórico", e a partir do dia seguinte só aparece o que abrir de novo.
5. **Quem arruma.** A aba `PENDENCIAS` vai para quem corrige. Precisa de mais alguma coisa, por exemplo o histórico do lançamento? Recomendo: não, por enquanto; o detalhe está nas abas `DET_*`.
