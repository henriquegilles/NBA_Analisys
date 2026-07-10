# Fase 1 — Absorção: conhecimento, auditoria e melhorias

> **Objetivo da fase:** capturar TODO o aprendizado da sessão de decisão fantasy (Bandeja
> de 3), auditar o que já existe no repo, e listar melhorias — antes de esquematizar e
> construir. Fio condutor: a franquia **Lobos Comunistas** (cod 528).

---

## 1. O propósito (o "porquê") — usando o Lobos como caso

O projeto existe pra responder **uma pergunta operacional em tempo real**:

> *"Dado meu elenco, a liga e o mercado, qual a melhor decisão AGORA (troca, FA, draft)?"*

Toda a sessão foi um piloto manual dessa pergunta. Exemplos reais que o motor precisa
sustentar:
- **Diagnóstico:** Lobos era #14/24, fundo (#18) em AST/3PM/TOV → veredito **punt TOV,
  ganhar 3PM**.
- **Troca:** Brunson+Sexton → Ja (tapou AST); Kuminga+Sharpe+2 picks futuras → **Donovan
  Mitchell** (tapou 3PM, virou contender).
- **Sell-high:** Avdija/Sharpe em declínio (concorrência Portland) → vender no pico.
- **Draft:** board **ajustado por oportunidade** (novato em rebuild >> talento em contender lotado).
- **Cap:** folha $126M / espaço $64M pós-trocas.

**Insight central:** todas essas decisões saíram de **métricas derivadas** (z-score por
categoria, valor punt-TOV, oportunidade, floor/ceiling) que hoje vivem em **scripts
pandas ad-hoc** — não versionadas. O objetivo do projeto é **materializar essas métricas
como views dbt** (reproduzíveis, testadas, alimentando dataviz).

---

## 2. O framework analítico (o conhecimento a preservar)

### 2.1 Regras da liga (governam tudo)
- **Dinastia, H2H por 7 categorias:** PTS, REB, AST, STOCKS (STL+BLK), 3PM, Plus/Minus, TOV (invertida).
- Vence quem leva **4+ categorias** no confronto → favorece **força concentrada + punting**.
- Cap **$190M**; **$0 na temporada = vai pra FA**; time só dá **match** de FA se for playoff.

### 2.2 Valoração por categoria (o coração)
- **z-score por categoria** sobre um **pool de referência** (rotação: G≥25, MP≥18).
- **TOV invertido** (menos é melhor). **STOCKS = STL+BLK**.
- **z_total** = soma dos 7 z (default oficial, D-22).
- **Valor punt-TOV (VA)** = `z_total − z_tov` — remove a categoria conscientemente
  concedida. **Métrica-chave do contexto do Lobos.**

### 2.3 Métricas derivadas validadas na sessão
| Métrica | Definição | Uso |
|---|---|---|
| **per-36** | stat/MP×36 → z sobre pool | achar valor escondido (bloqueado por minutos) |
| **Δ per-min** (`asym_permin`) | `z36 − z_total` | assimetria: produção/min ≫ bruta = breakout travado |
| **Development** | `VA − (idade−27)·0.35` | ajuste por idade (jovem bonificado) |
| **Opportunity** | `minutes_upside·3 + max(0,Δper-min)` | espaço de crescimento |
| **Floor/Ceiling** | percentis 20/85 do fantasy-score por jogo (gamelogs) | consistência/variância |
| **Risco (CV)** | desvio/média do fantasy-score por jogo | variância |
| **Fit posicional** | percentil de stocks/AST **dentro da posição** | raridade (ex.: playmaking de pivô) |

### 2.4 Camada de prospectos (draft)
- **college per-min + shooting indicators (3P%+FT%+volume) + playmaking + stocks + idade-relativa (class)**.
- **Modelo de comps** (k-NN sobre features normalizadas) → projeção NBA 6-cat (`fct_prospect_scouting`).
- **Ajuste por OPORTUNIDADE (D-novo):** multiplicar talento pela situação do time NBA
  **final (pós-troca)** — rebuild = minutos abertos = breakout; contender lotado = enterrado.
  **Erro pego na sessão:** o seed tinha o time de **draft-night**, não o final → corrigido manualmente.

### 2.5 Contexto NBA (camada externa)
- **Concorrência real** (ex.: logjam de Portland derruba Avdija/Sharpe) e **Summer League**
  (risers de rebuild) **não estão nos dados** — entram por pesquisa. Melhoria futura: seed de contexto.

---

## 3. Auditoria do estado atual

### 3.1 O que JÁ existe (reusar)
- **Seeds fantasy** (gitignored, do scraper `fantasy_gm.py`): `fantasy_rosters`, `_franchises`,
  `_standings`, `_draft_class`, `_draft_picks`, `_injuries`, `_trades` + `my_roster`, `fantasy_contracts`.
- **Camada de valoração NBA:** `int_player__fantasy_categories`, `fct_player_fantasy_value_season/_recent`.
- **Camada de prospectos:** `int_prospect__*`, `fct_prospect_scouting`, `fct_college_to_nba_outcomes`.
- **`fct_my_roster`** (marca meu elenco).
- **Dashboard Streamlit** existente (`dashboard/app.py`) — base pra estender.

### 3.2 GAPS (o que falta — vira o backlog)
1. 🔴 **Seeds fantasy sem camada dbt.** Não há `stg_fantasy__*` nem `int/mart` sobre os
   rosters/franquias/draft da liga. Toda análise de liga/FA/cap foi **pandas ad-hoc em `/tmp`**.
2. 🔴 **Sem views de métrica "em tempo real"** (roster valuation, força de liga por categoria,
   board de draft, alvos de FA, cap) → o dataviz não tem de onde beber.
3. 🟡 **Valor punt-TOV não é 1ª classe** no modelo (só z_total). O contexto do Lobos exige VA.
4. 🟡 **Oportunidade de draft (time NBA final)** é manual — precisa de seed versionado de landing spots.
5. 🟡 **Concorrência NBA / Summer League** não modelado (entra por pesquisa).
6. 🟢 **Reprodutibilidade:** os scripts pandas de `/tmp` devem virar SQL versionado.

---

## 4. Backlog de melhorias (priorizado)

| # | Melhoria | Fase | Valor |
|---|---|---|---|
| M1 | **Staging dos seeds fantasy** (`stg_fantasy__rosters/franchises/draft_class/picks`) | 2-3 | destrava tudo |
| M2 | **`int_fantasy__roster_valuation`** — junta meu roster × valoração 7-cat + VA punt-TOV | 3 | métrica do meu time |
| M3 | **`fct_league_category_strength`** — 24 times × categoria (rival scan) | 3 | contexto de liga |
| M4 | **`fct_fa_targets`** — disponíveis (FA/$0) ranqueados + regra de match (playoff) | 3 | alvos de FA |
| M5 | **`fct_draft_board`** — prospecto × projeção × **oportunidade (landing spot)** | 3 | board de draft |
| M6 | **`fct_team_cap`** — folha/espaço/vagas por franquia | 3 | cap em tempo real |
| M7 | **Seed `nba_landing_spots.csv`** (time NBA final pós-troca + tier de oportunidade) | 3 | corrige o erro de draft-night |
| M8 | **Prototype Streamlit** (FA + Draft) sobre as views | 5 | uso real |
| M9 | **VA punt-TOV como coluna** em `fct_player_fantasy_value_*` | 3 | 1ª classe |
| M10 | **README/estrutura/CI** de portfólio | 4 | apresentação |

---

## 5. Erros a revisar (durante e preditivamente)

Lições da sessão a codificar como **testes/guardrails**:
- ⚠️ **Acentos** quebram joins (Dončić/Jokić apareceram como FA). → **normalizar nome (NFKD)** em todo staging fantasy. **Teste:** 0 jogadores rosterados no pool de FA.
- ⚠️ **Unidades** (dólares cheios vs milhões) — bug no cálculo de cap. → **padronizar em $M** no staging de contratos. **Teste:** folha entre $0 e $200M.
- ⚠️ **Draft-night vs time final** — landing spot errado furou a análise de oportunidade. → seed versionado + **teste** de cobertura.
- ⚠️ **Dedup** — jogadores trocados no meio da temporada têm 2 linhas (TOT). → dedup por max-jogos no staging.
- ⚠️ **Confiança do modelo de prospecto é BAIXA** (poucos comps 2026) — expor `confidence` na view, nunca esconder.

---

## 6. Próximo passo → Fase 2 (Esquematização)

Desenhar as camadas: `seeds fantasy → stg_fantasy__* → int_fantasy__* → marts/views (fct_*/vw_*)`,
mapeando cada view do backlog (M2-M6) às suas fontes e à métrica que expõe pro dataviz.
Ver `02_esquematizacao.md`.
