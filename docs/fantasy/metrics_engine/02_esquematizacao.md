# Fase 2 — Esquematização: arquitetura das métricas

> Desenho das camadas que transformam os **seeds fantasy crus** + a **valoração NBA
> existente** em **views de métrica em tempo real** prontas pra dataviz e pro protótipo.

---

## 1. Fluxo de camadas (end-to-end)

```
SEEDS (scraper FantasyGM)           CAMADA NBA (já existe)
  fantasy_rosters ─┐                  fct_player_fantasy_value_season  (z 7-cat, VA)
  fantasy_franchises│                 fct_player_fantasy_value_recent
  fantasy_standings │                 fct_prospect_scouting  (projeção 6-cat)
  fantasy_draft_class│
  fantasy_contracts │                 SEED NOVO (versionado)
  seeds novos ──────┘                  nba_landing_spots.csv (time NBA final + opp tier)
        │                                      │
        ▼                                      │
  stg_fantasy__*  ◄── normaliza nome (NFKD), tipa, dedup, $ em milhões
        │                                      │
        ▼                                      ▼
  int_fantasy__roster_valuation ◄── JOIN roster × valoração (por nome normalizado)
  int_fantasy__available_players ◄── quem é FA ($0) / off-roster + regra de match
        │
        ▼
  MARTS / VIEWS (o que o dataviz consome)
   vw_my_roster_metrics      — meu time: VA por jogador + categoria
   fct_league_category_strength — 24 times × 7 categorias (rival scan)
   fct_fa_targets            — FA disponíveis ranqueados (fit punt-TOV) + match flag
   fct_draft_board           — prospecto × projeção × oportunidade (landing spot)
   fct_team_cap              — folha / espaço / vagas por franquia
```

**Materialização:** marts como **view** (métrica "em tempo real" — recalcula a cada `dbt
run`/query, refletindo o seed atualizado pelo scraper). Staging/intermediate podem ser view também.

---

## 2. Chave de junção (o ponto crítico)

- Seeds fantasy têm **`codigo_nba`** (id NBA.com) e **`nome_jogador`**.
- Camada NBA (`fct_player_fantasy_value_*`) tem **`bbr_id`** (slug Basketball Reference) e `player_name`.
- `codigo_nba` ≠ `bbr_id` → **junção por NOME NORMALIZADO** (NFKD, lower, sem pontuação).
- **Macro `norm_name()`** centraliza a normalização (evita o bug de acento Dončić/Jokić).

---

## 3. Especificação das views (contrato pro dataviz)

| View | Grão | Colunas-chave | Métrica que expõe |
|---|---|---|---|
| **vw_my_roster_metrics** | jogador do Lobos | nome, pos, idade, VA, z_pts…z_tov, salário | forças/fraquezas do MEU time |
| **fct_league_category_strength** | franquia × categoria | franquia, cat, z_soma (top-N), rank | quem vence cada categoria (rival scan) |
| **fct_fa_targets** | jogador disponível | nome, pos, VA, fit_punt_tov, larga_de, pode_dar_match | alvos de FA ordenados |
| **fct_draft_board** | prospecto | nome, arquétipo, proj_6cat, time_nba, opp_mult, score_ajustado | board de draft por oportunidade |
| **fct_team_cap** | franquia | franquia, folha_ano1, espaço, vagas | cap em tempo real |

---

## 4. Guardrails (testes que codificam os erros da sessão)

| Teste | Onde | Previne |
|---|---|---|
| 0 rosterados no pool de FA | `fct_fa_targets` | bug de acento (Dončić como FA) |
| folha ∈ [0, 200M] | `fct_team_cap` | bug de unidade ($ vs $M) |
| 0 duplicatas (franquia, jogador) | `stg_fantasy__rosters` | linhas TOT de trocados |
| `opp_mult` not null p/ prospecto c/ landing spot | `fct_draft_board` | draft-night vs final |
| `confidence` sempre exposto | `fct_draft_board` | esconder incerteza |

---

## 5. Próximo → Fase 3 (Construção)
Macro `norm_name` → `stg_fantasy__*` → `int_fantasy__*` → as 5 views + seed de landing spots + testes.
