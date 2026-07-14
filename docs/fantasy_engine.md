# Fantasy Decision Engine — Overview

An analytics layer built on top of the NBA warehouse to support roster decisions in
"Bandeja de 3", a private fantasy basketball league. It reuses the same stack as the rest of
the project — Python scrapers → CSV seeds → dbt models on PostgreSQL → Streamlit — and adds a
lightweight pandas engine for offline what-if simulation.

## The league

"Bandeja de 3" is a 24-team dynasty league hosted on the FantasyGM platform, played
**head-to-head by categories**: each weekly matchup is decided by whoever wins **4 or more of
7 statistical categories** — points, rebounds, assists, stocks (steals + blocks), three-pointers
made, plus/minus, and turnovers (inverted: fewer is better). Franchises operate under a
$190M salary cap with multi-year contracts, free agency, and a rookie draft.

League state (rosters, franchises, standings, draft class, picks, trades) is pulled by
`src/scraping/fantasy_gm.py`. The site is a React SPA, but it exposes an internal JSON REST
API; Selenium is used only to log in and capture the session token, after which plain
`requests` fetches everything — the full 24-franchise roster set comes from a single endpoint.
Outputs land as gitignored CSV seeds (anonymized samples are generated for CI, since dbt
`ref()`s to missing seeds fail at parse time).

## The 7-category z-score valuation

Category leagues reward *relative* production, so the core valuation is a **z-score per
category** computed over a reference pool of rotation players (minimum games and minutes-per-game
floors, to keep small-sample outliers from distorting the distribution):

- `z_<cat>` — how many standard deviations a player is above the pool mean in that category,
  with turnovers sign-flipped and steals + blocks combined into "stocks";
- `z_total` — the sum across all 7 categories (the official ranking metric);
- `VA` — `z_total` minus the z of a deliberately conceded ("punt") category, making
  punt-strategy value a first-class column instead of a spreadsheet afterthought.

Plus/minus is absent from Basketball Reference's per-game table, so it is derived by averaging
each player's game-by-game `plus_minus` from the ~26k-row gamelog seed. Two valuation windows
exist side by side: full season and recent form (last 15 games, with its own pool).

## dbt fantasy marts

The fantasy layer follows the project's standard staging → intermediate → marts flow
(`dbt/models/marts/fantasy/`). Fantasy seeds and NBA stats have no shared key (the league uses
NBA.com IDs, the warehouse uses Basketball Reference slugs), so joins go through a
`norm_name()` macro — NFKD-normalized, lowercased, alphanumeric-only — which also neutralizes
accented-name mismatches (Dončić, Jokić).

| Model | Grain | Purpose |
|---|---|---|
| `fct_player_fantasy_value_season` | player | 7-category z-scores + `z_total` + `VA`, full season |
| `fct_player_fantasy_value_recent` | player | same, over the last-15-games window |
| `vw_my_roster_metrics` | rostered player | the tracked franchise's roster joined to its valuation |
| `fct_league_category_strength` | franchise × category | top-N roster z-sums per category — who wins each category |
| `fct_fa_targets` | available player | free agents ranked by value and category fit |
| `fct_draft_board` | prospect | college-based projection × NBA landing-spot opportunity multiplier |
| `fct_team_cap` | franchise | payroll, cap space, and roster slots per franchise |

Marts are materialized as views ("live" metrics that pick up refreshed seeds on the next
build), and schema tests encode past bugs as guardrails: payroll must fall in $0–200M (catches
unit errors), zero rostered players may appear in the FA pool (catches name-join failures), and
roster staging must be duplicate-free (traded players ship as multiple rows upstream). The
draft board also carries an explicit `confidence` column from the prospect-comps model, so
projection uncertainty is surfaced rather than hidden.

## Win-probability simulation

`dashboard/fantasy_engine.py` is a self-contained pandas engine that reads the seeds directly —
no database required — and reproduces the valuation (pool z-scores, VA, per-36, floor/ceiling
percentiles from gamelogs). On top of it, the simulation module builds a **franchise × category
matrix** (summed z-scores of each roster's top players) and plays the tracked roster against
all 23 rivals deterministically: a category is won when the team total is higher, a matchup
when 4+ of 7 categories are won, and the **win probability is the fraction of rivals beaten**.

Two things fall out of this cheaply:

- **Category weights** — re-run the simulation with +1σ added to one category at a time; the
  winrate delta per category identifies which categories actually swing matchups, and those
  weights feed the free-agent fit score.
- **What-if evaluation** — any hypothetical move (trade, signing, draft pick) is scored as the
  winrate delta after swapping the affected players in the matrix.

Because the scrape is a point-in-time snapshot, the engine layers versioned override seeds on
load: trade overrides reassign players whose deals closed after the scrape, and NBA-context
overrides adjust team assignments (including a shrinkage correction to plus/minus for players
who changed NBA teams, since +/- is heavily team-dependent). Overrides are auditable in git and
become no-ops once a fresh scrape reflects reality.

## Streamlit decision panel

`dashboard/app.py` is the single entry point (`streamlit run dashboard/app.py`). Tabs split
into two families:

- **Seed-based tabs** (roster, projections, matchup analysis, free agency, draft board, league
  overview, cap) — powered by the pandas engine and always available offline; heavier boards
  are precomputed into `dashboard/data_cache/` so the UI reads cached CSVs instead of
  recomputing.
- **Warehouse tabs** (NBA averages/value, college stats, prospect scouting, comps) — query the
  dbt marts in PostgreSQL and degrade to a friendly warning when the database is down.

The whole app is covered by a headless smoke test (`dashboard/test_app_smoke.py`, built on
`streamlit.testing.v1.AppTest`) that executes every tab and fails on any uncaught exception —
which has caught missing-dependency and slow-query regressions before they reached the UI.
