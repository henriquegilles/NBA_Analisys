# Pendências de Validação — Rodada 6 (noite de 2026-07-11)

> Decisões de **regra de negócio** que eu (Claude) não executo sozinho. Cada entrada:
> contexto, recomendação única, alternativas, custo de errar em cada direção, prazo.
> O resumo executivo de 1 página será escrito no TOPO ao final da Fase 5.

# ⚡ RESUMO EXECUTIVO — as decisões da manhã (em ordem de urgência)

> Estado do motor: 7 categorias com +/- ajustado por contexto; baseline **69,6%**
> (16V 7D). Régua: ±4,3pp = empate técnico; sim determinístico ≠ probabilidade.
> Detalhes: doc 09 §18-§19. Vereditos do cético aplicados (§19.2).

| # | Decisão | Recomendação | Custo de adiar |
|---|---|---|---|
| 1 | **P-02: perguntar ao comissário a regra do $0 trocado** (posse ou só match?) e o critério de match de playoff | fazer HOJE — 1 mensagem destrava/mata os planos 1-2 e define o risco do Wiggins | cada dia sem resposta é um dia negociando às cegas; se alguém fizer a troca-modelo antes, o preço sobe |
| 2 | **P-05+P-03: abrir (ou não) a conversa Ja→MPJ com o SantoSpurs** | abrir SONDAGEM (sem oferta formal) já — plano nº 1 (95,7% teórico; +13pp só o MPJ). Levar adoçante orçado (pick 19 ou filler) e NÃO aceitar dar a pick 10 | o logjam do Ja em POR está na ESPN — o preço dele só cai a partir de agora |
| 3 | **P-04: tetos do leilão** | Wiggins faixa **$10-14M** (alvo nº 1 inegociável); **Quickley teto SUBIU para $22M** (perdê-lo = −21,8pp e mata o plano 1); LeBron só flyer ≤$4M (P-06 derrubada) | leilão sem teto escrito = decisão no calor; datas do FGM ainda não publicadas — anotar quando saírem |
| 4 | **P-01: rodar o scraper FGM** (exportar FGM_EMAIL/FGM_PASS) | rodar antes de QUALQUER oferta formal — os rosters são de 08/jul | propor troca com roster defasado = papelão + retrabalho |
| 5 | **Picks (informativo, sem urgência):** 13→Ament, 10→Lendeborg (manter), 19→Graves | já decidido no board; só executar no draft | — |

**O que NÃO foi feito nesta rodada (sem maquiar):**
1. **Scraper FGM não rodou** (sem credenciais) — toda a análise usa rosters de 08/jul.
2. **Tema "valor empírico de pick" da pesquisa não foi coberto** (agente travou); doc 10
   usa a curva própria da liga como mitigação.
3. **G-score/variância semanal NÃO implementado** (backlog nº 1 do doc 10) — por isso o
   sim não sabe precificar "margem" e a P-06 (LeBron) ficou sem sustentação quantitativa.
4. **As §0-§13 do doc 09 não foram reescritas** — receberam nota de revogação global +
   notas cirúrgicas nos pontos perigosos; os winrates antigos seguem no texto como
   registro histórico.
5. **Excedente do outro lado das trocas não é modelado** (crítica do cético): os dWin
   medem só o MEU ganho; a disposição do SantoSpurs/Namekusei é hipótese.
6. **Regras da liga não confirmadas nos dados:** $0 trocado (P-02), match de playoff,
   desempate de categoria empatada (0,0 tratado como não-vitória, conservador).

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

> ⚠️ **REVISADA 2x (doc 09 §17 e §18.3):** recomendação final = **NÃO fazer o
> Herro** (dominado: VA dele caiu a 0,98 no rebuild do MIL e o plano MPJ+Wiggins
> dá +30pp sem gastar a pick). Ficar com a pick 10 → Lendeborg (ramo B do leilão).

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
- **Recomendação (revisada §18.3):** Wiggins virou **alvo inegociável** (+17,4pp
  sozinho; presente em TODOS os planos vencedores): teto **$14M em qualquer ramo**.
  Quickley: teto **REVISADO para $22M** (§19.3: perdê-lo sem reposição = −21,8pp e o
  plano nº 1 cai de 95,7% pra 73,9% — o $18M era fóssil do motor 6-cat e subprecificava).
- **Alternativas:** (a) teto do Wiggins mais agressivo ($12M já no ramo A) aceitando
  1 filler a menos; (b) soltar Quickley de saída e realocar tudo em Wiggins + guard
  de 3PM barato.
- **Custo de errar:** teto baixo demais → perder o seguro do Avdija (single point of
  failure de SF, §3); teto alto demais → estourar a reserva de fillers e entrar na
  temporada com 2-3 vagas de mínimo sem verba.
- **Prazo:** antes do leilão (data ainda não publicada no FGM — anotar quando sair).

## P-05 — Janela de venda do Ja Morant

> ⚠️ **REFORÇADA pela correção do +/- (doc 09 §17):** o VA do Ja caiu de 2,4 pra
> 1,7 (z_PM −0,7) — o argumento de vender ANTES da temporada ficou mais forte.

- **Contexto:** Ja projeta só 1,07 de VA em 2026-27 (logjam POR + amostra G=20 —
  §15.4), mas o NOME ainda vale mais que o número. Três cenários de venda no §16.4
  (nº 1 Namekusei, nº 3 SantoSpurs, nº 5 Nadal) — os dois primeiros com dWin real.
- **Recomendação (revisada §18.3):** vender ANTES da temporada, destino preferencial
  **SantoSpurs (MPJ)** — plano nº 1 do §18.1, sem bloqueio de regra. Namekusei
  (Anunoby) vira alternativa se a P-02 liberar. Nota: o ajuste de +/- recuperou o
  VA do Ja pra 2,4 (POR ≫ MEM) — vender é win-now defensável, não urgência de pânico.
- **Alternativas:** (a) segurar até a deadline apostando que POR resolve o logjam
  (Lillard tem 36a — pode ser buyout/banco); (b) vender por pick futura em vez de
  jogador, acumulando capital de draft 2027.
- **Custo de errar:** vender barato demais → o mercado esquece o G=20 e o Ja de 24-25
  pts volta em outro contexto; segurar → 3 meses de box scores a 0,90 de mult
  derretem o preço.
- **Prazo:** janela ideal = entre o draft da liga e a 1ª semana da temporada.

## P-06 — LeBron no leilão: o veto caiu (+17,4pp) — lance até quanto?

- **Contexto:** com o +/- no motor (doc 09 §17), o LeBron sozinho vale **+17,4pp**
  (60,9%→78,3%, 4 confrontos) — o veto da rodada 4 ("+0,0pp") era artefato do sim
  de 6 categorias. Ele está a $0 no Capão da Canoa (não é o protegido deles),
  contrato de 1 ano, 41 anos, VA 7-cat de 6,4 com PM +2,0/jogo.
- **Recomendação (FINAL, pós-cético §19.2 — a versão "$12M de reserva" foi DERRUBADA):**
  LeBron = **flyer oportunista ≤$4M** se ninguém disputar, nada além. +4,3pp = empate
  técnico pela nossa própria régua; +0,0 em cima do plano nº 1; 41 anos sem destino NBA
  definido. Reavaliar SÓ depois do G-score (variância semanal) e de ele assinar na NBA.
- **Alternativas:** (a) teto agressivo ~$30M se os cenários de troca (P-02/P-03)
  morrerem — ele vira O reforço da janela; (b) não entrar: 41 anos é o maior risco
  de cliff da liga e o modelo não cobre ano-42 (heurística — não verificado).
- **Custo de errar:** não dar lance → deixar 4 confrontos/ano na mesa por medo de
  um cliff que pode não vir em UM ano; pagar caro demais → num cliff estilo
  pós-38 (queda de 30%+), vira $25M+ de folha morta numa temporada de contender.
- **Prazo:** leilão (data a confirmar no FGM).
