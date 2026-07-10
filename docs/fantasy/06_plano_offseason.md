# Plano de Offseason — Lobos Comunistas (Bandeja de 3)

> Documento de **decisão** da offseason 2026-27. Ancorado nos dados raspados do
> FantasyGM em 2026-07-08 (runbook #27) + valoração por categoria (aproximação do
> Domínio A em pandas, stats NBA 2025-26). Franquia **Lobos Comunistas** (cod 528,
> usuário 218) · Liga **Bandeja de 3** (cod 24, 24 times) · Temporada **81 (2026-27)**.
>
> ⚠️ Números de categoria = **aproximação** (2025-26, sem plus/minus, novatos sem
> stats). O modelo oficial (`fct_player_fantasy_value_season` + `fct_prospect_scouting`)
> roda quando o **Docker/Postgres** subir — ver §8.

---

## 1. Regras que governam tudo

**Dinastia, head-to-head por 7 categorias** — vence quem levar a maioria (4+):

| PTS | REB | AST | STOCKS (STL+BLK) | 3PM | Plus/Minus | TOV (menos é melhor) |
|---|---|---|---|---|---|---|

O jogo é **vencer 4+ categorias no maior número de confrontos** — favorece força
concentrada e **punting** consciente de 1-2 cats fracas.

**Cap (confirmado na API):** teto **$190M** · folha Ano 1 **$144,5M** · **espaço $45,5M**
· elenco **18/18 (cheio)** · **zero multas** hoje. **11 dos 18 contratos expiram após o Ano 1.**

**Mecânica-chave (regra do usuário):** jogador com **salário $0 nesta temporada = vai
para Free Agency**. Vale pra todos os times — cada um decide quem renova.

---

## 2. Onde o Lobos está na liga (rank por categoria, 24 times)

| Categoria | Rank | Leitura |
|---|---|---|
| **REB** | **#6** 🟢 | Força real (Claxton, Ware, Stewart, Cardwell) |
| **PTS** | **#8** 🟢 | Força (Brunson, Sexton, Sharpe, Kuminga, Avdija) |
| **STOCKS** | #10 🟡 | Competitivo |
| **AST** | **#18** 🔴 | Fundo — refém do Brunson |
| **3PM** | **#18** 🔴 | Fundo — o buraco (ironia da liga) |
| **TOV** | **#18** 🔴 | Fundo — scorers alto-uso viram bola |
| **GERAL** | **#14/24** | Meio de tabela (subestimado: upside dos novatos não entra) |

**Diagnóstico:** time de **garrafão + pontos** que perde as 3 **categorias de
guarda-habilidade** (AST, 3PM, TOV), todas empatadas em #18. Não é azar — é o perfil.

---

## 3. VEREDITO ESTRATÉGICO — Punt TOV

TOV está **amarrado aos seus scorers** (Brunson/Sexton/Sharpe alto-uso); ganhá-la exige
bancá-los. Não vale. Então:

1. **Punt TOV** (concede de propósito).
2. **Ancore em PTS + REB + STOCKS** — seu núcleo 🟢/competitivo = **3 categorias**.
3. **Ganhe a 4ª tapando 3PM** (mais fácil de comprar que profundidade de AST; e é o
   tema da liga). **AST** vira bônus em cima do Brunson.

Efeito colateral bom: como você **punta TOV**, armadores alto-uso (que viram bola) ficam
**alvos ideais** — o único defeito deles é a categoria que você já concedeu.

---

## 4. Elenco atual — quem fica, quem renova, quem vai

Com Brunson **mantido** (ancora PTS/AST/3PM, seus pontos frágeis).

**Contratados (multi-ano / com salário):** Brunson ($52M, expira após Ano1),
Kuminga ($29M×2 — ver §5), Claxton ($16,5M), Sharpe ($14M), Avdija ($11,2M, **seu
melhor custo-benefício**), Sexton ($9,9M), Ware ($7,2M, ótimo valor jovem),
Traore (R $5M×3), Sion James (R).

**Renovações (jogadores $0 → FA):** só **1 vale a pena.**

| 🟢 Renovar | 🔴 Deixar ir (nível-reposição; substituíveis na FA) |
|---|---|
| **Peyton Watson** (ala jovem, Stocks +1,1, único fit +) | LaRavia · I. Stewart · Cardwell · Caleb Love · Huerter · Nembhard · Spencer Jones · Jaylen Clark |

> Nembhard tem o único AST+ do grupo (+1,3) mas afunda no resto → tapa-se AST melhor
> na FA/draft. Libere os 8, abra vagas e cap pros upgrades.

---

## 5. Kuminga — ✅ FAZER O BUYOUT (multa confirmada = ~$7M)

Troca **não é opção** (usuário tentou até com picks; ninguém assume o contrato; peça
banida de troca). Sobrava manter-e-bancar vs buyout — e a **multa foi confirmada no site
em ~$7M garantido**. Decisão fechada: **BUYOUT.**

- Multa $7M sobre $58M restantes = **~12%**, muito abaixo do limiar de 1/3 (~$19M).
- Valor de categoria já **negativo** (zTOT −0,86, abaixo da média em 4/6 cats) → cortá-lo
  **não custa quase nada em quadra**.

**Efeito no cap (financia a FA):**

| | Antes | Após buyout |
|---|---|---|
| Folha Ano 1 | $144,5M | $144,5M − $29M + $7M = **$122,5M** |
| **Espaço no teto** | $45,5M | **~$67,5M** |
| Vaga de elenco | 18/18 | **17/18 (1 vaga)** |

Troca um clogger de $29M/valor-negativo por $7M mortos + ~$22M de espaço + 1 vaga. Com
~$67M você **cabe no tier máximo (~$35M)** e passa a brigar de verdade por um armador
AST+3PM estrela na FA (§6). **O buyout é o passo que financia o conserto do seu buraco.**

*(Limiar de referência: buyout ≤~1/3 do restante = fazer; ~1/2 = borderline; ≥~2/3 = não.
Kuminga caiu folgado no "fazer".)*

---

## 6. Free Agency — o pool tem estrela solta

Com "$0 = FA", o mercado inclui os $0 de TODOS os times — e há **estrelas** disponíveis.
Ordenado pelo fit punt-TOV (AST+3PM priorizados, TOV ignorado):

| Alvo | Pos | Fixa | Larga de | Realista? |
|---|---|---|---|---|
| **Luka Dončić** | PG | PTS+AST+3PM (sonho punt-TOV) | Green Cinnamon (#22) | ✅ time ruim |
| **Jokić / LeBron** | C/F | tudo | Capão da Canoa (#24, lanterna) | ✅ reconstrução |
| **Cade Cunningham** | PG | **AST+3PM**, jovem | SantoSpurs (#1) | ⚠️ contender segura |
| **Jamal Murray** | PG | AST+3PM+PTS | São Paulo (#12) | 🟡 talvez |
| **Grayson Allen / Gillespie / Rollins** | G | 3PM barato | contenders | ⚠️ prováveis renovações |

**Lógica:** contenders **renovam suas estrelas** (igual você renova o Watson). Quem
**cai de verdade** são as estrelas dos **times em reconstrução** → **Capão (Jokić,
LeBron), Green Cinnamon (Luka), fire-sale do Havana**. **Miles!** — KPJ e Miles Bridges
estão **banidos** (fora). **Prioridade: um armador AST+3PM** (Cade é o fit de idade+cat;
Luka se vencer o leilão).

Logística: baratos vão no tier de ~$2M; corte scrubs pra abrir vaga; cabe nos $45,5M.

---

## 7. Draft — pick provável **#19**

Classe que entra: **94 novatos** (44 G / 36 F / 14 C) — via **draft**, não FA. Pelo
consenso 2026, no #19 os bigs/alas de topo já foram; sobram **armadores** (= sua
necessidade). Preferência pro seu perfil (**AST + 3PM + baixo TOV**):

1. **Braden Smith (Purdue, PG)** — motor de AST + roubos + bom 3P, TOV baixíssimo. Se
   cair até o 19, **é ele**.
2. **Bennett Stirtz (PG organizador)** — outro distribuidor, tapa AST.
3. **Labaron Philon Jr. / Brayden Burries** (combo guards c/ handle + arremesso).
4. Jaylin Sellers / Emanuel Sharp (scorers — menos AST, menos ideais).

**Regra pra pick 19:** pegue o **melhor armador-organizador na tela** (Braden Smith /
Stirtz > combo guards). Draft rico em guarda = via natural p/ consertar AST/3PM com upside.

*(Board: Rookie Scale Consensus 2026 · ESPN Top 100.)*

---

## 9. Free Agency, Buy-Low e Regras de Contrato (análise 2026-07-08)

> Fit = valoração punt-TOV (PTS+REB+STOCKS +1,5·AST +1,5·3PM, TOV ignorado). Camada
> NBA = situação real 2026-27 (movimentos do offseason 2026). Realismo = quem cada
> franquia da liga tende a soltar ($0 de time em reconstrução cai; contender renova).

### 9.1 Regras de contrato — mín/máx para NÃO estourar o cap

**Tiers de lance da liga (FA):** mín **$2M** (1 ano); faixas $2–10M/$10–20M/$20–35M
regem a **duração** (1→3 anos). **Teto de lance = $70M** (confirmado pelo comissário
2026-07-08 — o $35M das faixas era bracket de duração, não o limite). Quanto maior o
lance, mais anos.

> ⚠️ Teto da liga ($70M) **> seu espaço** (~$67,5M). Logo **o limite prático é o SEU
> cap**, não a regra — e ainda precisa sobrar pra preencher o elenco (ver 9.1.1).

**Seu orçamento seguro (pós-buyout Kuminga):** espaço **~$67,5M**, elenco **17/18**.

| Regra | Número |
|---|---|
| Teto duro (nunca ultrapassar a folha) | **$190M** |
| Folha após buyout | $122,5M |
| **Espaço para gastar (Ano 1)** | **~$67,5M** |
| Reservar (renovação Watson + preencher últimas vagas no mínimo) | ~$8M |
| **Teto prático de gasto em FA** | **~$60M** |
| Máx num único atleta | **$70M** (limite da liga) — mas seu teto real é o espaço |
| Máx viável no Lobos (e ainda montar time) | **~$50M** (ponto ótimo $40–45M) |
| Mín por assinatura | **$2M** |

**Não-faça-burrada:**
1. Nunca deixe a soma das folhas do Ano 1 (elenco + novas assinaturas + renovações)
   passar de **$190M**. Você está em $122,5M → pode adicionar até ~$67,5M, mas **pare
   em ~$60M** (buffer p/ mínimos in-season).
2. **Brunson ($52M) sai após o Ano 1** → Ano 2 você terá espaço enorme. Contratos
   multi-ano são OK **se o Ano 1 couber**; não precisa ter medo de comprometer o Ano 2.
3. **Renovação do Watson:** ele é role player → renove no **tier mínimo (~$2M)**, não
   pague de titular.
4. Regra de ouro: **1 estrela no máx ($35M) + 1 peça média (~$15M) + preencher no
   mínimo** cabe folgado. Ou espalhe (~$20M+$18M+$12M) em 3 fits.

### 9.2 20 alvos de FA para monitorar (ordem de prioridade p/ o Lobos)

Precisa AST+3PM, punt TOV, dinastia (juventude conta), ~$67M. "Cai?" = realismo.

> **REGRA DE MATCH (confirmada 2026-07-08):** o time atual **só pode igualar o lance se
> estiver no playoff**. Logo: **$0 de time NÃO-playoff = gettable de verdade** (não
> iguala); **$0 de time playoff = pode ser igualado** (evitar brigar). Isso torna o
> **Luka** (Green Cinnamon, não-playoff) o alvo mais limpo, e o **Cade** (SantoSpurs #1,
> playoff) mais difícil do que a tabela sugere. Teto de lance da liga = **$70M**, mas
> seu máximo viável ≈ **$50M** (ótimo $40-45M).

| # | Jogador | Pos/Id | Custo | Fit / papel | Cai? + contexto NBA 2026-27 |
|---|---|---|---|---|---|
| 1 | **Luka Dončić** | PG/26 | $35M | 🐐 PTS+AST+3PM — punt-TOV perfeito | ✅ Green Cinnamon (#22 reconstrói). **Swing máximo.** |
| 2 | **Cade Cunningham** | PG/24 | $30–35M | Conserta AST (#18), jovem | ⚠️ SantoSpurs (#1) pode segurar — monitorar |
| 3 | **Jamal Murray** | PG/28 | $25–30M | AST+3PM+PTS no auge | 🟡 São Paulo (#12) |
| 4 | **Ryan Rollins** | PG/23 | $2–8M | **Jovem barato AST+3PM+stocks** | 🟡 Victory Village. **Melhor custo-eficiência** |
| 5 | **Immanuel Quickley** | PG/26 | $12–18M | AST+3PM guard | ⚠️ SantoSpurs pode segurar |
| 6 | **Jaylen Brown** | SF/29 | $25–30M | PTS+3PM | 🟡 Baião (#16). NBA: **trocado p/ Philadelphia**, papelão ↑ |
| 7 | **Nikola Jokić** | C/30 | $35M | Elite tudo (mas você é fundo em C) | ✅ Capão (#24 lanterna) |
| 8 | **Dyson Daniels** | SG/22 | $8–14M | Jovem, **Stocks elite** + AST | 🟡 Vasconha. Líder de roubos |
| 9 | **Grayson Allen** | SG/30 | $4–8M | **Especialista de 3 (need)** | ⚠️ Marujos (#3) |
| 10 | **Lauri Markkanen** | PF/28 | $18–25M | PTS+3PM stretch-4 | ⚠️ Partizan (#2) segura |
| 11 | **Evan Mobley** | PF/24 | $18–25M | Jovem, Stocks (DPOY-type) | 🟡 Pupunha (#18) |
| 12 | **Collin Gillespie** | PG/26 | $2–6M | AST+3PM barato | 🟡 Baurulhos (#4) |
| 13 | **OG Anunoby** | F/28 | $10–16M | 3-and-D (3PM+stocks) | 🟡 Namekusei (#7) |
| 14 | **Brandin Podziemski** | SG/22 | $6–12M | Jovem 3PM+AST upside | 🟡 Elfos (#5) |
| 15 | **Naz Reid** | C/26 | $8–14M | Stretch-5 (3PM+stocks) | ⚠️ SantoSpurs |
| 16 | **Onyeka Okongwu** | C/25 | $8–14M | Jovem C, stocks+REB | 🟡 Pass2will (#19) |
| 17 | **Kevin Durant** | SF/37 | $20–28M | Scorer+3PM elite | 🟡 Victory Village. Idade 37 |
| 18 | **Jalen Green** | SG/23 | $8–14M | Jovem scorer+3PM | 🟡 Rondonópolis. Nova situação NBA |
| 19 | **Moses Moody / Cam Spencer** | SG | $2–5M | 3PM barato de preenchimento | 🟡 vários |
| 20 | **LeBron James** | SF/41 | $12–20M | AST+PTS | ✅ Capão solta, mas **deixou os Lakers**, destino/idade = dart |

**Leitura:** persiga **1 armador do topo (1-5)** com o gasto grande; complete com
**Rollins/Gillespie/Grayson (3PM+AST baratos)** pra encher o carrinho sem estourar.

### 9.3 Buy-low via troca — "em baixa que vai disparar" (contexto NBA)

Jovens em outros rosters, subvalorizados agora, com papel crescente em 2026-27. Moeda:
suas **picks (incl. #19)** + os 8 expirings de $0. Alvo nº 1 casa com seu buraco (3PM):

| Jogador | Pos/Id | Está em | Por que dispara (NBA 2026-27) |
|---|---|---|---|
| **Reed Sheppard** ⭐ | SG/21 | Marujos | **Papel expandido em Houston**, 39% de 3 em volume, proj ~15/4,8/2+ triplos. **Casa com seu 3PM.** Alvo nº 1 |
| **Matas Buzelis** | PF/21 | Minnesota TL | Uso explodiu após Chicago vender veteranos (22,4/7,2 nos últimos 5) |
| **Keyonte George** | PG/22 | Minnesota TL | AST+3PM ascendente (breakout esperado) |
| **Amen Thompson** | PG/23 | **Havana (fire-sale)** | Estrela em ascensão; **Havana desmontou o time → mais barato de tirar** |
| **Stephon Castle** | PG/21 | Blank Space Jam | Papel garantido ao lado do Wemby, breakout de alta probabilidade |
| **Brandon Miller** | SF/23 | São Paulo | 3PM 1,9; estava estourando antes de lesão — buy-low de recuperação |
| **VJ Edgecombe / Bub Carrington** | G/20 | SantoSpurs / São Paulo | Armadores jovens com minutos crescentes |

**Jogada de mercado:** o **Havana Comrades está em fire-sale** (dispensou o time todo)
— é o alvo nº 1 pra raidar buy-low (Amen Thompson, Max Christie). E **Reed Sheppard** é
o único buy-low que **conserta seu 3PM** — vale gastar pick pra ele.

*Fontes NBA: Yahoo/Athlon Fantasy 2026-27 sleepers; NBA.com/ESPN 2026 offseason trackers.*

---

## 8. Próximos passos (quando o Docker subir)

O passo 1-2 "oficiais" estão bloqueados: **Docker inativo** neste WSL → Postgres não sobe.
Pra destravar: abrir Docker Desktop + WSL integration, depois `docker compose up -d postgres`.

1. **Domínio A oficial** sobre `my_roster` — confirma os z-scores **com plus/minus**.
2. **`fct_league_category_strength`** (novo) — ranking dos 24 times por categoria como
   modelo dbt (hoje é pandas).
3. **`fct_prospect_scouting`** cruzado com `fantasy_draft_class` — ranqueia os **94
   novatos por fit de 6-cat** (o preciso pra pick 19).
4. **Multa exata do buyout do Kuminga** (`/franquia/simular/jogador/...`) quando o
   mercado abrir — crava a decisão da §5.

---

## TL;DR da decisão

- **Identidade:** punt TOV; ganhe PTS+REB+STOCKS+3PM. · **Brunson:** manter.
- **Kuminga:** ✅ **BUYOUT** (multa só $7M) → espaço vai a **~$67,5M** + 1 vaga. · **Renovar:** só Watson.
- **FA:** com ~$67M, brigue por armador AST+3PM estrela (Cade/Luka/Murray) + 1 atirador de rotação.
- **Pick 19:** melhor armador-organizador (Braden Smith → Stirtz → Philon/Burries).

---

## 10. PLANO FINAL EXECUTÁVEL (fechado 2026-07-09)

> Consolidação de tudo — supera decisões parciais das seções acima quando houver conflito.
> Análise quantitativa completa nos cards: `07_player_cards.md` (422 NBA) + `08_prospect_cards.md` (94/94).

### 10.1 Estado atual (pós-trocas)
- ✅ **Ja Morant** adquirido (Brunson + Sexton + 2ª → Ja + #10 + #13). **AST resolvido.**
- **Elenco mantido:** Ja, Traore, Sharpe*, Avdija*, Sion James, Watson, Kuminga(hold), Claxton, Ware. (*SELL-high)
- **Picks:** #10, #13, #19 · **Cap:** amplo (~$70-97M conforme Kuminga).

### 10.2 Correções que mudaram o plano
- **Concorrência Portland:** Ja+Sharpe+Avdija no mesmo time NBA → **Avdija e Sharpe DESVALORIZAM** (Portland tirou o papel de armador-ala do Avdija; Sharpe "dispensável"). → **SELL-HIGH os dois.**
- **Board por OPORTUNIDADE (não só stats):** novato em rebuild (minutos abertos) >> mesmo talento em contender lotado. **Times finais pós-troca** (não draft-night — seed a corrigir).
- **Summer League 2026:** confirmou os risers de rebuild (Peterson, Acuff, Anderson, Burries). Reed Sheppard entrou no All-SL → **encareceu**.

### 10.3 Decisões travadas
| Item | Decisão final |
|---|---|
| Tapar **3PM** | **Pelo DRAFT** (custo zero) — não depender de troca |
| **Avdija + Sharpe** | 🔴 **SELL-HIGH** (antes do logjam Portland derrubar) |
| **Kuminga** | ⏸️ **HOLD** — gatilho Lakers titular→flip; senão buyout ($7M) |
| Sheppard/Keyonte (troca) | ❌ só se pechincha (draft resolve de graça) |
| **FA** | atiradores baratos de time não-playoff + banca o resto |

### 10.4 Draft (âncoras — risers de rebuild)
- **#10:** Peterson/Dybantsa/Mikel Brown se caírem; senão **Brayden Burries** (Milwaukee rebuild)
- **#13:** **Christian Anderson** (Charlotte rebuild — "star in plain sight" na SL)
- **#19:** **Brayden Burries** ou **Darius Acuff** (Sacramento, líder de pontos SL)
- ❌ Fora: Labaron Philon (Philly lotado), Isaiah Evans (Minnesota lotado) — landing spots ruins.

### 10.5 Ordem de execução
1. Travar board do draft (3PM resolvido).
2. Avdija + Sharpe no bloco → colher ofertas (jovem+pick de contender).
3. Kuminga: monitorar Lakers (~10-15 jogos).
4. FA: 1-2 atiradores baratos + banca cap.

### 10.6 Tese central
Punt TOV · dominar **PTS+REB+STOCKS** · tapar **3PM pelo draft** · vender Avdija/Sharpe no pico · segurar Kuminga pelo upside Lakers. Objetivo: **vencer 4+ das 7 categorias por confronto**.
