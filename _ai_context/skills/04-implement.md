# SKILL `/implementar` — implement + tdd (Matt Pocock, adaptada ao chat-only)

> Cole dentro de `<SKILLS_ATIVAS>`. Já inclui as skills `tdd` (com as regras de teste e de mock) e o vocabulário de `codebase-design` que a original chama. A skill `code-review` roda à parte, em conversa nova (`/review`).
> `<TAREFA_ATUAL>` deve conter **um ticket** (e, se couber, as seções da spec que ele usa).

## Objetivo
Implementar **um ticket**, com as checagens escritas **antes** do código. Uma conversa = um ticket.

## Passos

1. **Declare o título do ticket antes de começar.** Se a referência for ambígua, pergunte. Confira se os tickets listados em "Bloqueado por" estão `done` (Doc Mestre/`<TAREFA_ATUAL>`); se não, pare e avise.

2. **Combine os *seams* antes de qualquer teste.** Escreva os seams que serão testados (pontos públicos onde se observa o comportamento sem olhar dentro: o contrato de uma função, a tabela/arquivo de saída, uma view SQL, uma medida DAX), cada um com uma linha do que **pega** e do que **não pega**. Normalmente já estão nos critérios do ticket e nas "Decisões de Teste" da spec; confirme com **uma pergunta só**, com a sua recomendação ("sim" aceita). **Nenhum teste é escrito em seam não confirmado.** Não dá para testar tudo: combinar os seams antes é o que põe o esforço nos caminhos críticos e na lógica complexa.

3. **Plano enxuto** (regra 3.4): `1. [passo] -> verificar: [CHECK e resultado esperado]`.

4. **O laço vermelho → verde (TDD), em fatias verticais.** Um seam, um teste, uma implementação mínima por ciclo; cada teste é um *tracer bullet* que responde ao que o ciclo anterior ensinou. Como você não executa nada, o `aplicar.py` executa o laço por você:
   * (a) grava os testes/checagens do ciclo; (b) **roda e espera FALHOU** (vermelho) e imprime `CHECK <nome> vermelho esperado: OK`; (c) grava a implementação **mínima**; (d) **roda de novo e espera OK** (verde).
   * Se um ticket tem comportamentos independentes, entregue **um ciclo por mensagem**. Ciclos pequenos e dependentes podem ir no mesmo script, na ordem.
   * No fim do último ciclo: rode **todas** as checagens do ticket (a "suíte completa" uma única vez) e grave tudo em `resumo_verificacao.txt`.
   * Se o projeto usa verificação de tipos ou linter (registrado no Doc Mestre), rode no fim também.
   * **Refatorar não faz parte do laço**: pertence à etapa de revisão (`/review`).

5. **FALHOU?** Diagnostique só pelo **nome** da checagem e pelo sinal da diferença (positiva/negativa/zero), nunca por valores (regra 2). Entregue a correção em um único `aplicar.py`.

6. **Tudo OK? Finalize no mesmo script** (bloco abaixo): commit **local** só dos arquivos criados e gravação do diff para a revisão. Nunca dados, saídas ou `.scratch/`; nunca `git add -A`; nunca `push`. O script também marca o ticket como `Status: done`.

   ```python
   import subprocess
   from pathlib import Path

   def finalizar(arquivos, mensagem, feature, todos_ok):
       """Commit local só dos arquivos criados + grava o diff para o /review."""
       def git(*a):
           return subprocess.run(["git", *a], capture_output=True, text=True)
       if not todos_ok:
           print("CHECK commit: PULADO (há checagens FALHOU)"); return
       if not Path(".git").exists():
           print("CHECK commit: PULADO (sem repositório git)"); return
       base = git("rev-parse", "HEAD").stdout.strip()
       git("add", "--", *arquivos)
       r = git("commit", "-m", mensagem)
       print("CHECK commit criado:", "OK" if r.returncode == 0 else "FALHOU")
       if r.returncode == 0:
           diff = git("diff", base, "HEAD").stdout
           out = Path(".scratch") / feature / "review.diff"
           out.parent.mkdir(parents=True, exist_ok=True)
           out.write_text(diff, encoding="utf-8")
           print("CHECK diff gravado:", "OK" if diff.strip() else "FALHOU")
   ```
   Mensagem do commit: `ticket NN: <título>`. `arquivos` = lista explícita dos arquivos de código/teste criados. (Se o projeto ainda não tem commits, pule o diff e avise.)

7. **Chame o review:** como o `code-review` original, ele deve rodar com contexto limpo. Termine dizendo: *"Abra uma conversa NOVA, cole `00-rules.md` + `05-code-review.md` + Doc Mestre + spec + `review.diff` e digite `/review`."* E lembre: `/fechar` nesta conversa para registrar o estado no Doc Mestre.

## Regras de teste (tdd)

**O que é um bom teste.** Verifica **comportamento por interfaces públicas**, não detalhes de implementação. O código pode mudar inteiro e o teste não deve quebrar. Lê como uma especificação ("a saída final contém uma linha por operação") e sobrevive a refatorações.

**Anti-padrões:**
- **Acoplado à implementação:** simula colaboradores internos, testa funções privadas ou verifica por canal lateral (consulta o banco em vez de usar a interface). Sinal: o teste quebra num refactor sem mudança de comportamento.
- **Tautológico:** o esperado é recalculado do mesmo jeito que o código (passa por construção e nunca discorda dele). O esperado vem de **fonte independente**: um literal conhecido, um exemplo resolvido à mão, a spec, ou outro caminho (ex.: SQL vs Python). Nas checagens OK/FALHOU, as duas pontas devem ser independentes.
- **Fatiamento horizontal:** escrever todos os testes primeiro e toda a implementação depois. Testes em bloco verificam comportamento *imaginado*. Faça fatias verticais: um teste → uma implementação → repete.

**Regras do laço:** *Vermelho antes de verde* (teste que falha primeiro, depois só código suficiente para passar; nada especulativo). *Uma fatia por vez.* *Refatorar não é parte do laço.*

**Quando simular (mock):** só em **fronteiras do sistema**: conexões de banco (ex.: Oracle), APIs externas, tempo/aleatoriedade, sistema de arquivos (às vezes). **Nunca** simule seus próprios módulos nem colaboradores internos. Projete para ser simulável: receba as dependências por parâmetro (injeção) em vez de criá-las dentro da função, e prefira uma função por operação externa em vez de um "buscador" genérico. Dados de teste são **sintéticos**, inventados por você (regra 1.2).

## Vocabulário de design (codebase-design, resumido)
Use os termos com exatidão; quando discutir a forma de uma interface, esta é a referência:
- **Módulo**: qualquer coisa com interface e implementação (função, classe, pacote). **Interface**: tudo que quem chama precisa saber (assinatura, invariantes, ordem, erros, configuração), não só a assinatura. **Seam**: onde a interface do módulo vive e onde dá para alterar comportamento sem editar ali.
- **Módulo profundo** = muito comportamento atrás de uma interface pequena (bom). **Raso** = interface quase tão complexa quanto a implementação (evite). A interface é a superfície de teste: se quer testar *além* dela, o módulo provavelmente tem a forma errada.
- **Teste da exclusão:** imagine apagar o módulo. Se a complexidade some, era só repasse; se reaparece espalhada em N chamadores, ele se pagava.
- **Um adaptador = seam hipotético; dois = seam real.** Só crie um seam se algo realmente varia por ele.
- **Projete para testar:** aceite dependências, não as crie; retorne resultados, não produza efeitos colaterais; interface pequena.

▶️ Termine com `▶️ Sua vez:` dizendo qual a próxima ação do usuário (rodar `python _ai_context/aplicar.py` e colar `resumo_verificacao.txt`).
