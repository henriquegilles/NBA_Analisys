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
- **📰 Update 13/jul (Micah Nori, novo HC do POR):** declarou publicamente que mantém
  os 4 armadores e vai jogar **Lillard+Ja JUNTOS**, com Jrue na 3 (como fez 3 anos no
  Pelicans). Dois efeitos: (a) o cenário-desastre "Ja no timeshare/banco" enfraquece —
  ele titula com proteção de aro (Clingan+Rob Williams) e spacing do Dame, então
  SEGURAR ficou menos catastrófico; (b) mais importante: a narrativa pública virou
  POSITIVA — comprador lê "Ja titular confirmado", o medo do logjam que derrubava o
  preço amoleceu. **É o melhor momento da janela pra executar a escada P-08b — usar a
  fala do Nori como argumento de venda.** O número do motor não muda (VA 2,4 já
  assumia contexto POR com posse dividida em 3).

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

## P-07 — Luka Dončić está exposto no leilão ($0 no Green Cinnamon, sem proteção): lance até quanto?

- **Contexto (achado pós-fechamento, pergunta do Henri sobre a melhor FA):** Luka a $0,
  NÃO protegido (Green Cinnamon não consta na lista de restritos), VA 12,5 no motor
  final — o maior valor disponível da liga inteira. Melhor FA pura: **Luka + Wiggins
  = 91,3%** (e torna o Quickley dispensável: sem ele dá os MESMOS 91,3%, liberando os
  $22M da reserva). Plano B pelo mesmo número: **Mobley + Wiggins = 91,3%** (Mobley
  exposto no Pupunha). Stack com a troca Ja→MPJ = 23V 0D teórico.
- **Recomendação:** teto **~$45M** no Luka (fecha em $65M com Wiggins $14M + fillers,
  sem reserva do Quickley). Se passar disso, migrar SEM dó pela escada de degraus —
  todos terminam em 91,3%: **B) Mobley até $27M** (só ele já dá 91,3%; exige reserva
  do Quickley de volta — sem Luka, perdê-lo derruba pra 82,6%); **C) Wiggins $14M +
  Dyson Daniels ~$8M** (o barato: 22a, stocks+PM de elite, exposto no Vasconha —
  exceção documentada à regra anti-guard, o perfil defensivo dele é o que falta).
- **Alternativas:** (a) all-in $55M+ (cabe no teto de $70M/atleta mas mata o Wiggins —
  e só Luka = 87,0% < Luka+Wiggins); (b) ignorar o Luka e manter o plano Quickley $22M
  + Wiggins (82,6%).
- **Custo de errar:** teto baixo → perder o melhor ativo da liga por $2-3M; teto alto →
  virar time de 1 estrela + fillers (o sim diz que o PAR vale mais que a estrela só).
- **Prazo:** leilão. Perguntar junto com a P-02 se o Green Cinnamon (17º) tem direito
  de match (regra de playoff).

#### Update 13/jul — "e se trocar o Mitchell pelo Luka?" (pergunta do Henri)

- **Sims:** swap seco = 73,9% (+4,3pp, 1 confronto = ruído); swap + Wiggins = 87,0%;
  **swap + plano completo (Wiggins+Okongwu ou Wiggins+Daniels) = 91,3%** vs plano
  atual completo com Mitchell = 87,0%.
- **MAS: Wiggins + Daniels no leilão, SEM tocar no Mitchell, dá os MESMOS 91,3%**
  (verificado de novo hoje). O swap não adiciona teto nenhum que o leilão puro já
  não alcance — e adiciona dois riscos: (i) regra da liga: o Luka é expirante $0 —
  trocar o Mitchell por ele só faz sentido se os DIREITOS DE RENOVAÇÃO transferirem
  na troca (pergunta P-02; se não transferem, você deu o Mitchell por um direito de
  dar lance e pode perder o Luka no leilão = catástrofe −34,8pp); (ii) $/VA: sai um
  $54M contratado, entra um leilão de ~$55M — neutro financeiro na melhor hipótese.
- **Leitura financeira honesta:** o swap é o único caminho que torna o Luka PAGÁVEL
  (all-in mantendo Mitchell: Luka ~$55M + Quickley $22M = $77M > $69M de espaço,
  não fecha; com o swap a folha cai pra $67M e espaço vai a $123M — Luka + plano
  inteiro cabem com folga). Se o Henri QUISER o Luka por tese dynasty (26a vs 29a
  do Mitchell), o swap é o mecanismo certo — mas o ganho de winrate é zero vs
  Wiggins+Daniels, então é decisão de preferência, não de modelo.
- **Recomendação:** não fazer. Prioridade segue o leilão (Wiggins + Daniels se o
  Okongwu estourar $20M). Reavaliar só se a P-02 confirmar transferência de direitos
  E o Green Cinnamon aceitar (motivo pra ele: perder o Luka de graça no leilão vs
  receber o Mitchell contratado).

## P-08 — Oferta viva: Brandon Miller por Claxton + pick 13 + pick 19 (São Paulo Galaxy)

- **Contexto (negociação real, 2026-07-11 à noite):** Galaxy pediu Ware ou Avdija;
  Henri ofereceu Claxton + picks 13 e 19. Miller: 23a, VA 5,1, z-3PM 1,83 / z-PM
  1,37 (nossas duas cats perdidas), $35,4M/ano. **Sim da troca seca: +0,0pp**
  (69,6% → 69,6% — REB cai de 3,3 pra 2,4 e nenhum confronto flipa; as derrotas de
  3PM são por margens de −5 a −9). Combos pós-troca rendem MENOS que os mesmos
  leilões sem ela (Miller+Wiggins 82,6% vs MPJ+Wiggins 95,7%). Miller cancela o
  Wiggins (anti-sinergia de perfil) e deixa $50,1M de espaço (sem Luka).
- **Recomendação:** NÃO fechar como está. Contraoferta **Claxton + pick 19 apenas**
  (com Miller no elenco, a 19/Graves vira redundante — a necessidade que ela cobria
  é o próprio Miller; a 13/Ament segue sendo nosso ativo dynasty de frontcourt).
- **Alternativas:** (a) Claxton + 13 + 19 SÓ SE devolverem um jovem big de REB no
  pacote; (b) recusar e executar o plano vigente (MPJ+Wiggins, 95,7%, zero picks);
  NUNCA Ware (vender no fundo, −4,3pp na troca) nem Avdija (intocável).
- **Custo de errar:** fechar caro → 2 firsts + $19M/ano de folha extra por +0,0pp
  na temporada da janela; recusar um Miller barato → perder um titular de 4 anos
  nas duas cats estruturalmente fracas (o valor dele é DYNASTY, não 2026-27).
- **Prazo:** enquanto a conversa está quente — mas a pressa é DELES (rebuild
  precisa de picks); cada dia sem fechar não piora nosso plano A.

### P-08b — Contraproposta do Galaxy: Avdija por Miller + MPJ (atualização da negociação)

- **Sims:** proposta seca = 78,3% (+8,7pp; 3PM resolvido −1,5→+2,6, mas AST cai
  4,4→3,2 e Wiggins deixa de somar). **CONTRA "Ja + Claxton → Miller + MPJ"
  (Avdija fica) = 82,6%, e com Wiggins no leilão = 95,7%** — o mesmo teto do plano
  vigente COM o Miller (23a) de bônus dynasty; cap fecha em $123,7M (espaço $66,3M).
- **Recomendação:** escada — (1) Ja+Claxton por Miller+MPJ; (2) Ja+Claxton+pick 19;
  (3) só então discutir a proposta original (trocar 2 confrontos de 2026-27 por
  janela futura — decisão de estratégia do Henri, não do modelo).
- **⚠️ Verificação obrigatória antes de fechar:** nos dados de 08/jul o MPJ pertence
  ao SANTOSPURS, não ao Galaxy — confirmar dono atual (P-01: rodar o scraper) e se
  é troca de 3 times (regras de encadeamento da liga).
- **Custo de errar:** dar o Avdija ($11,2M×2, 25a, melhor contrato do elenco) quando
  Ja+Claxton compravam o mesmo pacote = perder o ativo errado; travar demais e o
  Galaxy recuar = perder a melhor janela de consolidação que apareceu até agora.

### P-08c — Nova oferta do Galaxy (13/jul, WhatsApp): Avdija por Miller + Jaquez (ou McDaniels + Jaquez)

- **Contexto:** Galaxy trocou o MPJ da P-08b por **Jaime Jaquez ($10,1M/2y)** e, "se o
  Miller estiver caro", oferece **Jaden McDaniels ($8,5M/2y)** no lugar. Prazo dado: "até 2".
- **⚠️ Mesma pegadinha do MPJ:** no snapshot de 08/jul o Jaquez é do **Kush City Dope**
  e o McDaniels é do **JF Bagres** — o Galaxy só é dono do Miller. Ou o snapshot está
  velho (P-01: rodar o scraper) ou é de novo troca encadeada de 3 times.
- **Sims (baseline 69,6%; REF P-08b reproduzido em 82,6%/95,7% ✓):**
  | Cenário | Seco | + Wiggins |
  |---|---|---|
  | A. Avdija → Miller+Jaquez (oferta) | 73,9% | **73,9%** (Wiggins não soma nada) |
  | B. Avdija → McDaniels+Jaquez (variante) | 69,6% | **65,2%** (piora!) |
  | C. contra: Ja+Claxton → Miller+Jaquez | 73,9% | 78,3% |
  | D. contra: Ja+Claxton → Miller só | 73,9% | 82,6% |
  | REF: Ja+Claxton → Miller+MPJ (P-08b) | 82,6% | **95,7%** |
- **Leitura:** o Jaquez tem **VA −0,9** (abaixo de replacement — é salário, não peça);
  a troca MPJ→Jaquez custa sozinha 13-17pp de teto. A variante McDaniels (VA 1,3) é
  pior que não fazer nada. E dar o Avdija (VA 5,3) por Miller (VA 5,1) trava o teto em
  73,9% porque perde AST/REB/TOV que o Wiggins não repõe (anti-sinergia já vista na P-08).
- **Folha:** oferta A = +$34,3M/ano (155,3M; espaço cai de $69M pra $34,7M) — **mata o
  plano de leilão travado ($64M no pior caso)**. Contra D = +$13,0M/ano (folga mantida).
- **Recomendação:** RECUSAR as duas. Manter a escada da P-08b: **Ja + Claxton por
  Miller + MPJ** (Avdija não sai). Se ele alegar que não tem o MPJ, cobrar: ele também
  não tem o Jaquez nem o McDaniels — se sabe encadear 3 times pra eles, sabe pro MPJ.
  Fallback se MPJ for impossível: **Ja + Claxton por Miller seco** (82,6% com Wiggins,
  igual ao plano de leilão atual, com Miller 23a de bônus dynasty) — e o Jaquez NÃO
  entra nem de graça (ocupa vaga de roster com VA negativo).
- **Argumento de venda:** usar a fala do Nori (update P-05 de 13/jul) — "Ja titular
  confirmado ao lado do Dame" — pra defender o valor do pacote Ja+Claxton.

#### Update (13/jul, noite): Ja está FORA do negócio; Galaxy tem as picks 8 e 9

- **Fatos novos:** o Ja não entra no pacote (escada P-08b morta) e o Galaxy segura
  as picks **8 e 9** desta classe.
- **Sims sem o Ja (baseline 69,6%):**
  | Cenário | Seco | + Wiggins |
  |---|---|---|
  | E. Claxton (+pick) → Miller | 69,6% | **82,6%** |
  | F. Claxton+Stewart → Miller | 69,6% | 82,6% |
  | G. Claxton+Huerter → Miller | 65,2% | 78,3% |
  | H. Claxton (+picks) → Miller+MPJ | **82,6%** | 73,9% (Wiggins PIORA aqui) |
  | I. Avdija → Miller + picks 8+9 | 65,2% | 82,6% |
- **Conclusão central: sem o Ja, TODO caminho de trade tem teto 82,6% —** abaixo dos
  87,0% do plano de leilão travado. Trade agora é jogada de DYNASTY (Miller 23a,
  picks), não de janela; só fazer se o preço for barato.
- **Curva de picks (insight de mesa):** a faixa 8→13 é chapada — pick 8 ≈ 16,6 de
  produção esperada, 9 ≈ 17,0, nossa 13 ≈ 16,2. E nesta classe o penhasco é no top-5;
  pelo board, a nossa 13 ainda pega o **Ament (score 23,2)**, MELHOR que o take
  esperado nas posições 8-9 (~17-21). Não deixar o Galaxy vender 8/9 como ouro.
- **Recomendação (em ordem):**
  1. **Claxton + pick 19 → Miller** (contra da P-08 segue viva): janela neutra no
     seco, 82,6% com Wiggins, Miller de bônus dynasty, mantém 13/Ament. Folha +$18,9M
     (espaço 69→50,1) → **Okongwu ($20M) não cabe mais** — realocar pro Daniels ou
     guardar; Quickley+Watson+Wiggins+fillers ($44M) seguem cabendo.
  2. Se ele insistir no Avdija: preço mínimo = **Miller + pick 9** (ancorar em 8+9).
     Sim = 82,6% com Wiggins (mesmo teto), Miller 23a + top-10 pick de volta. É
     decisão janela-vs-dynasty do Henri: troca 87,0%→82,6% em 2026-27 por ativos.
  3. Jaquez NÃO entra em nenhum cenário (VA −0,9, ocupa vaga); McDaniels idem.
- **Cuidado no H:** se ele encadear MPJ sem o Ja, 82,6% SECO é o melhor puro-trade —
  mas aí NÃO assinar Wiggins (cai pra 73,9%, excesso de alas no top-10); realocar o
  lance. E folha vai a $156,1M (espaço 33,9) — só Quickley+Watson+fillers cabem.

#### Sensibilidade: "e se o report do Avdija estiver certo?" (perda de posse com o Ja em POR)

- **Contexto NBA:** Avdija é POR (24,2/6,9/6,7 como hub em 2025-26). A trade do Ja
  mandou **Grant e Murray (as duas alas) pra MEM** → os MINUTOS dele estão mais
  seguros que antes; o risco é POSSE (Nori: 3 armadores juntos, Jrue na 3). O sim
  usa z 2025-26 cru — o mult 0,90 do seed só afeta os predicts, não a valoração.
- **Teste de corte nas stats de posse (PTS/AST/3PM/TOV):** −10% → 60,9%; −15% →
  60,9%; −25% (desastre) → **60,9%. O dano satura em −8,7pp** — flipa 2 confrontos
  justos e para: o resto do estrago cai em PTS/AST (cats com folga) e o TOV dele
  (nosso pior z pagante) MELHORA com menos posse, compensando.
- **Com o Wiggins do plano: 82,6% — desconto 100% absorvido** (mesmo número do
  Avdija cheio; o perfil PTS/3PM do Wiggins cobre exatamente o que o corte tira).
- **Vender por Miller no mundo descontado: 82,6% também** — vender não protege
  NADA na janela, mesmo se o report for verdade.
- **Única assimetria a favor de vender:** o VA de mercado dele (5,3) cai pra
  3,8-4,3 se a posse encolher — o preço NUNCA estará mais alto que agora. Se um
  dia for vender, é antes da temporada, a preço cheio (Miller + pick 9, mínimo) —
  nunca em dezembro com box scores fracos na mesa.

---

# ✅ DECISÃO DO HENRI (2026-07-11, noite) — plano de leilão travado

**Foco: renovar Quickley + Watson, assinar Wiggins; se sobrar, Okongwu.**
(Supersede a parte de leilão das P-04/P-07; as trocas P-08 seguem em negociação à parte.)

| Prioridade | Peça | Teto | Efeito |
|---|---|---|---|
| 1 | **Quickley** (renovação/leilão) | **$22M** | protege tudo — perdê-lo = −21,8pp |
| 2 | **Watson** (renovação, restrito) | ~$2M | jovem no caminho (§16.8) |
| 3 | **Wiggins** | **$14M** | +13pp → 82,6%; seguro do Avdija |
| 4 | **Okongwu** (se sobrar) | **$20M** | pacote completo = **87,0%** e fio 13→10 |
| — | fillers (3 vagas de mínimo) | ~$6M | REB/ala (Valančiūnas/Strus §16.9) |

**Orçamento no pior caso (todos no teto): $64M de $69M — fecha com $5M de folga.**

Notas de execução:
- Se o **Okongwu** estourar $20M: **Dyson Daniels é upgrade, não consolação**
  (Wiggins+Daniels = 91,3% no sim, 22 anos, provavelmente mais barato) — trocar de
  alvo sem dó.
- **Não** gastar o troco em Goodwin se o Okongwu vier (sim: adicionar o 3º cai pra
  82,6% — efeito de composição do top-10; guardar o resto pro meio da temporada).
- Se a negociação P-08b (Ja+Claxton → Miller+MPJ) fechar, o Wiggins fica redundante
  (anti-sinergia de alas) — nesse caso realocar o lance dele pro Okongwu/Daniels.

## P-09 — Mesa nova (ideia do Henri, 13/jul): Claxton + picks 13+19 por Walker Kessler (Baurulhos)

- **Kessler:** 24a, VA **7,8** (2º do elenco se vier), $14,7M/y, z-REB 2,78 + STOCKS
  3,32 + PM 1,91 — a alavanca de REB em dose de elite. Primeira troca da rodada em
  que pagar as DUAS picks se justifica.
- **Sims:** seco **82,6%** (+13pp, maior salto seco testado); **+ Wiggins = 95,7%**
  (teto com UM lance de leilão); Daniels/M.Robinson ficam redundantes (91,3% — não
  assinar). Folha MELHORA (−$1,8M; espaço 70,8). Não depende da regra P-02.
- **Régua:** abrir com Claxton+19; subir pra +13 se travar; recuar se pedirem
  Ware/Watson/pick futura. Ressalva: Baurulhos é contender — se toparem rápido,
  fechar antes que reconsiderem.

## P-10 — Avdija por pick top-3 (tese do Henri, 13/jul): vale, COM ordem de operações

- **Valor:** classe com penhasco pós-top-5 (Dybantsa 39,7 / Peterson 36,5 / Boozer
  29,0 vs Ament 23,2); top-3 > Avdija em moeda dynasty. Tese validada.
- **Janela:** sem Avdija, leilão puro tem teto 87,0% ($42M). MAS **sem Avdija +
  Kessler (P-09) + Wiggins + Daniels = 95,7%** — mesmo teto do plano, com top-3 no
  bolso (espaço $82M, leilão $46M).
- **Condições:** (1) fechar o Kessler ANTES ou junto — sem ele a venda do Avdija
  rebaixa a janela; (2) pick 1-2 sem hesitar, pick 3 com adoçante; (3) confirmar o
  dono das picks — seed com ordem zerada (escolha=0), rodar P-01 antes; (4) risco
  empilhado consciente: 2 trocas + 2 lances vs plano atual que chega a 95,7% sozinho;
  números otimistas em ~1 confronto (comprador do Avdija não modelado).
