# Camada Fantasy — Documento de Escopo

> **Status:** rascunho de design (ideação). Nenhum código/modelo foi criado ainda — este documento captura apenas escopo e decisões.
> **Contexto da liga:** ver regras completas em "Regras Fantasy Bandeja de 3" (Liga B.D.3, site fantasy.ciengos.com).
> **Data de início da discussão:** 2026-06-18.

---

## 1. Objetivo

Construir, por cima do data warehouse de NBA já existente, uma **camada analítica de apoio à decisão** para a liga de fantasy **Bandeja de 3**.

O site da Ciengos já roda a liga de verdade. Este projeto **não recria o motor da liga** — ele **agrega inteligência por cima dos stats da NBA** para ajudar o GM a tomar melhores decisões.

**Foco:** uma única franquia (o time do Henri), não a liga inteira.

---

## 2. Como a liga pontua (fundamento estatístico)

A liga é **dinastia, head-to-head por categorias**. Cada confronto compara dois elencos em **7 categorias**; vence quem ganhar a maioria delas.

| # | Categoria da liga | Origem nos stats NBA | Observação |
|---|---|---|---|
| 1 | Pontos | `pts` | — |
| 2 | Rebotes | `trb` | — |
| 3 | Assistências | `ast` | — |
| 4 | STOCKS | `stl` + `blk` | soma de roubos + tocos |
| 5 | Bolas de 3 | `three_p` | cestas de 3 convertidas |
| 6 | Plus/Minus | `plus_minus` | — |
| 7 | Turnovers | `tov` | **menos é melhor** (única invertida) |

**Estado atual do modelo:** `fct_player_game_log` (grão = 1 jogador × jogo) **já expõe todas as 7 categorias**. A fundação de stats para pontuar por categoria está pronta.

---

## 3. Restrição estrutural: site congelado

O site Ciengos está em **freezing** — **não é possível exportar nada dele**. Consequência direta de modelagem:

- ✅ **Viável:** tudo que depende só de stats da NBA (já scrapeados do Basketball Reference).
- ❌ **Bloqueado:** tudo que depende do **estado da liga** — rosters das outras 23 franquias, contratos-fantasy, calendário de confrontos, classificação. Não há fonte.

Isso limita análises que precisam saber "quem está em qual time" (ver §4, caso *Alvos de FA*).

---

## 4. Domínios e casos de uso

A camada cobre **dois domínios analíticos distintos**.

### Domínio A — Otimização da minha franquia
Baseado nos stats da NBA. Alguns casos precisam do meu roster (ver §6).

| Caso de uso | Viabilidade | Depende de |
|---|---|---|
| **Valoração por categoria** — ranquear jogadores da NBA pela contribuição nas 7 categorias (TOV invertido) | 🟢 Total | só stats NBA |
| **Forças/fraquezas do meu elenco** — em quais categorias meu time é forte/fraco | 🟡 | meu roster |
| **Avaliação de trocas** — trocar X por Y melhora meu perfil de categorias? | 🟡 | meu roster |
| **Alvos de Free Agency** — quem pegar pra cobrir fraquezas | 🟠 Limitado | sem dados da liga, só dá pra aproximar como "melhores fora do meu time" |

### Domínio B — Scouting de draft (prospectos)
Avaliar jogadores universitários/prospectos para escolher no draft de calouros da liga. **Precisa de fonte de dados nova** — o scraping atual é só NBA.

- **Filosofia:** scouting **híbrido e comparativo** (ver decisão D-04).
- **Fontes faseadas:** NCAA → G-League → Internacional (ver decisão D-06).

---

## 5. Decisões tomadas (decision log)

| ID | Decisão | Racional |
|---|---|---|
| **D-01** | Propósito = **ferramenta de análise/decisão**, não réplica do motor da liga | O site já roda a liga; o valor está em inteligência por cima dos stats |
| **D-02** | Foco = **só a minha franquia** | Mais simples, menos dependência de dados externos indisponíveis |
| **D-03** | Janela temporal = **forma recente (últimos N jogos) E temporada cheia, lado a lado** | Decisões de fantasy precisam de quem está "quente" agora vs. base estável |
| **D-04** | Scouting = **híbrido comparativo**: proxy das 6 categorias sourceáveis + contexto (idade, eficiência, nível de competição, uso) + comparação com prospectos históricos e seus desfechos na NBA | Stats de college não traduzem 1:1 pra NBA; comparar com histórico é o jeito mais honesto de dar significado |
| **D-05** | Modelar **base histórica college→NBA** como espinha dorsal das comparações | Sem histórico, a avaliação da classe atual fica crua e sem referência |
| **D-06** | **Fasear** fontes de prospecto: **Fase 1** NCAA + histórico + framework; **Fase 2** G-League; **Fase 3** Internacional (via seed manual dos top prospects) | O framework é agnóstico de fonte — fasear sequencia o esforço de scraping sem limitar abrangência. Internacional é o mais caro/inconsistente |

---

## 6. Pontos em aberto

| Tema | Situação |
|---|---|
| **Fonte do meu roster** | A definir. Site congelado impede export. Henri mencionou poder enviar uma **imagem do time** futuramente (transcrição manual → seed pequeno de 12–18 jogadores). Decidir mais pra frente. |
| **Contratos-fantasy / cap ($190M)** | Não decidido se entram. Atenção: `dim_player_contract` tem **salário real da NBA**, que é **diferente** do contrato-fantasy. Não confundir. |
| **Posições oficiais** | Regras usam `nba.com/players` (até 2–3 posições/jogador). Modelo atual tem `dim_player.position` do BBR (aproximação). Definir se precisamos da fonte oficial. |
| **"N" da forma recente** | Quantos jogos definem "forma recente" (ex.: 10, 15)? A decidir na modelagem. |
| **Plus/Minus em prospectos** | Estrutural: **não existe** em college/internacional. Uma das 7 categorias fica de fora no scouting — documentar como limitação assumida. |

---

## 7. Faseamento geral (visão macro)

1. **Fase 1 — Núcleo da minha franquia + Scouting NCAA**
   - Marts de valoração por categoria (Domínio A, parte que só precisa de stats NBA)
   - Framework de scouting + fonte NCAA (College Basketball Reference) + base histórica college→NBA
2. **Fase 2 — Roster da minha franquia**
   - Ingestão do meu elenco (fonte a definir) → forças/fraquezas, trocas, alvos de FA aproximados
   - Scouting G-League
3. **Fase 3 — Internacional**
   - Seed manual dos top prospectos internacionais

---

## 8. Próximos passos (na conversa de design)

- [x] Modelar o **Domínio A** (marts de categoria) — feito/validado 2026-06-19 (z-score 7 cats, TOV invertido, STOCKS=stl+blk, forma-recente vs. temporada). 86 testes verdes.
- [x] Desenhar o **framework de scouting** (Domínio B) — feito 2026-06-19; backbone college→comps→outcomes→projeção, com 6-cat completo (D-30) e overrides (D-09), escalado p/ 18 escolas em 2026-06-21.
- [x] Definir a fonte e o modelo do **histórico college→NBA** — College Basketball Reference por escola × temporada (D-27) + desfecho do seed `draft`/carreiras NBA (D-29/D-30).
- [ ] Resolver os pontos em aberto da §6 conforme forem ficando relevantes — restam só os que dependem de dados externos (roster, classe de draft).
