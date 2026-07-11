# Pendências de Validação — Rodada 6 (noite de 2026-07-11)

> Decisões de **regra de negócio** que eu (Claude) não executo sozinho. Cada entrada:
> contexto, recomendação única, alternativas, custo de errar em cada direção, prazo.
> O resumo executivo de 1 página será escrito no TOPO ao final da Fase 5.

<!-- RESUMO_EXECUTIVO_PLACEHOLDER — preenchido na Fase 5 -->

---

## P-01 — Dados da liga possivelmente defasados: scraper FantasyGM não rodou (sem credenciais)

- **Contexto:** o brief pedia re-rodar `src/scraping/fantasy_gm.py` antes de tudo, mas
  `FGM_EMAIL`/`FGM_PASS` não estão no ambiente desta sessão. Toda a Rodada 6 usa os
  seeds fantasy da última coleta (ver tabela de frescor na Fase 0 do doc 09).
- **Recomendação:** de manhã, exportar as credenciais e rodar o scraper + rebuild
  (`python src/scraping/fantasy_gm.py && dbt build --profiles-dir .dbt --select +models/marts/fantasy`),
  depois conferir se alguma conclusão da Rodada 6 muda (em especial rosters de rivais e
  standings — o resto é estável).
- **Alternativas:** (a) aceitar os dados atuais se você sabe que não houve movimentação
  na liga desde a última coleta; (b) pedir a outro membro da liga um print dos rosters
  recentes pra conferência manual.
- **Custo de errar:** se rodar de novo à toa → ~10 min. Se NÃO rodar e houve trade/waiver
  na liga → perfis de rivais e sugestões de troca da Fase 3 podem mirar jogadores que já
  mudaram de dono (retrabalho da análise, risco de propor troca inválida).
- **Prazo:** antes de agir em qualquer sugestão de troca da Fase 3.

---

## P-02 — Confirmar a REGRA da liga: jogador a $0 (expiring) trocado muda de dono ou vai a leilão mesmo assim?

- **Contexto:** a melhor troca do sim (Ja → Namekusei por **Anunoby + Pritchard**,
  +21,7pp, doc 09 §16.4 nº 1) envolve o Anunoby, que está a **$0 E é o restrito do
  Namekusei**. Se trocar por um $0 só transfere o "direito de match" (e não a posse),
  a troca vale muito menos do que o sim diz. O mesmo vale pro Wiggins ($0 nos Marujos).
- **Recomendação:** perguntar ao comissário ANTES de qualquer conversa com o Namekusei:
  (1) $0 trocado permanece com o novo dono na temporada? (2) o status de "restrito"
  viaja junto na troca?
- **Alternativas:** (a) renegociar a troca pedindo Pritchard ($6,45M contratado) +
  outra peça contratada, sem o Anunoby; (b) desistir do cenário 1 e ir pro cenário 3
  (MPJ, $16,2M contratado — mesma dWin do Herro sem gastar pick).
- **Custo de errar:** fechar a troca sem saber → pagar o Ja por um jogador que vai a
  leilão aberto (perda seca de até ~2,4 de VA). Não perguntar e desistir → deixar
  +21,7pp (5 confrontos) na mesa.
- **Prazo:** antes de abrir QUALQUER negociação com Namekusei/Marujos.

## P-03 — Executar (ou não) o plano A: pick 10 pelo Herro ($27,5M/1a, Baurulhos)

- **Contexto:** dWin +8,7pp (2 confrontos), blinda as vitórias por um fio de PTS/3PM.
  O mercado da pick 10 recuperou (Burries 18 pts na SL — §13.2). Herro tem só 1 ano
  de contrato ($27,5M) — é aluguel caro de curto prazo.
- **Recomendação:** manter o plano A (§16.5 ramo A), MAS só fechar depois de resolver
  a P-02 — se o cenário 1 (Anunoby) for viável, ele domina o Herro (+21,7 vs +8,7) e
  a pick 10 vira Lendeborg no ramo B.
- **Alternativas:** (a) ramo B: ficar com a pick → Lendeborg e buscar MPJ via troca
  do Ja (cenário 3 — mesma dWin sem pick); (b) leiloar a pick 10 pra outro comprador
  (preço médio de 1ª rodada na liga: $34M em jogadores).
- **Custo de errar:** fechar Herro cedo demais → perder o cenário dominante (1) por
  falta de folga de cap; esperar demais → Baurulhos usa a pick 10 de outro jeito e o
  hype do Lendeborg o tira do board.
- **Prazo:** decidir a ordem (P-02 primeiro) já; execução até a véspera do draft da liga.

## P-04 — Tetos de lance no leilão: Wiggins até quanto? Quickley até quanto?

- **Contexto:** §16.5. Wiggins ($0, desprotegido — Marujos protegeram Diabaté) é o
  seguro do Avdija e alvo nº 1 de leilão; dWin +8,7pp. Quickley é NOSSO expiring
  disputável (plano C se passar de $18M).
- **Recomendação:** Wiggins: teto **$8M** no ramo A / **$12M** no ramo B / $14M no C.
  Quickley: teto **$18M** — acima disso, soltar (AST é nossa categoria mais folgada;
  Nembhard cobre reposição).
- **Alternativas:** (a) teto do Wiggins mais agressivo ($12M já no ramo A) aceitando
  1 filler a menos; (b) soltar Quickley de saída e realocar tudo em Wiggins + guard
  de 3PM barato.
- **Custo de errar:** teto baixo demais → perder o seguro do Avdija (single point of
  failure de SF, §3); teto alto demais → estourar a reserva de fillers e entrar na
  temporada com 2-3 vagas de mínimo sem verba.
- **Prazo:** antes do leilão (data ainda não publicada no FGM — anotar quando sair).

## P-05 — Janela de venda do Ja Morant

- **Contexto:** Ja projeta só 1,07 de VA em 2026-27 (logjam POR + amostra G=20 —
  §15.4), mas o NOME ainda vale mais que o número. Três cenários de venda no §16.4
  (nº 1 Namekusei, nº 3 SantoSpurs, nº 5 Nadal) — os dois primeiros com dWin real.
- **Recomendação:** vender ANTES da temporada começar (antes que o logjam de Portland
  vire estatística visível), priorizando cenário 1 (se P-02 liberar) > 3 > manter.
- **Alternativas:** (a) segurar até a deadline apostando que POR resolve o logjam
  (Lillard tem 36a — pode ser buyout/banco); (b) vender por pick futura em vez de
  jogador, acumulando capital de draft 2027.
- **Custo de errar:** vender barato demais → o mercado esquece o G=20 e o Ja de 24-25
  pts volta em outro contexto; segurar → 3 meses de box scores a 0,90 de mult
  derretem o preço.
- **Prazo:** janela ideal = entre o draft da liga e a 1ª semana da temporada.
