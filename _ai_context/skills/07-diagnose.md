# Arquivo: skills/07-diagnose.md

## /diagnose
Quando eu digitar `/diagnose`, conduza uma investigação rigorosa para encontrar a causa raiz de um bug (Python/SQL/DAX), falha de pipeline ou divergência de números.

### Regra Central e Segurança
- **Sem reprodução confiável não existe diagnóstico:** É proibido chutar correções ou teorizar causas antes de termos uma forma rápida e determinística de reproduzir a falha.
- **Proteção de Dados (`<REDACTED>`):** Antes de eu colar qualquer log, traceback ou saída de banco, lembre-me de substituir senhas, strings de conexão, tokens e dados reais de clientes por `<REDACTED>`.

### Siga estritamente as 6 fases (sem pular etapas):
1. **Fase 1 — Reproduzir:**
   - Peça o comando executado, o traceback/erro exato mascarado, as versões do ambiente e o resultado esperado vs. resultado obtido.
   - Ajude-me a criar um script ou teste local mínimo com **dados sintéticos fabricados** que reproduza exatamente o sintoma (se for intermitente, fixe seeds aleatórias e datas de corte).
2. **Fase 2 — Reduzir (Isolamento):**
   - Com o erro reproduzindo, guie o corte de colunas, joins, filtros e etapas intermediárias, uma por vez, até restar o menor caso possível que ainda falha.
3. **Fase 3 — Hipóteses Falsificáveis:**
   - Liste de 3 a 5 hipóteses ordenadas da mais provável para a menos provável.
   - Toda hipótese deve ser declarada no formato falsificável: *"Se [Causa X] for verdadeira, então ao checar/mudar [Variável Y] observaremos [Resultado Z]"*.
   - Pergunte se houve alguma alteração recente ou rota já descartada na Seção 7.2 do Doc Mestre que reordene a lista.
4. **Fase 4 — Instrumentar (Uma variável por vez):**
   - Proponha 1 sonda cirúrgica por hipótese (asserts, queries de contagem/soma por etapa, `breakpoint()` ou logs pontuais nas fronteiras).
   - **Regra do Prefixo de Limpeza:** Todo `print` ou log de depuração inserido no código deve conter uma tag única (ex.: `[DEBUG-a4f2]`) para ser localizado e removido facilmente depois.
   - **Se o problema for lentidão:** Meça primeiro (`time.perf_counter`, `cProfile`, tamanho de dataframes pós-join ou `EXPLAIN PLAN` no SQL) antes de sugerir qualquer otimização.
5. **Fase 5 — Corrigir e Travar (Regressão):**
   - Somente após confirmar a causa raiz com a saída da instrumentação, entregue a correção cirúrgica (Diretriz Karpathy 1.3).
   - Entregue junto um teste automatizado (`pytest`) ou checagem de validação que falharia com o bug original e passa com a correção.
6. **Fase 6 — Limpar e Registrar Memória:**
   - Instrua a remoção de todos os blocos `[DEBUG-...]` e arquivos temporários.
   - Guarde todas as hipóteses que foram testadas e refutadas durante o diagnóstico para registrá-las em **7.2. Rotas Descartadas** no diff do fim da conversa.
