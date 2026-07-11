# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NBA basketball analytics portfolio project using dbt for SQL transformations, PostgreSQL as the data warehouse, Python (Selenium) scrapers for Basketball Reference, and Dagster to orchestrate the scraping + dbt pipeline.

## Python Environment

The project uses a virtual environment at `.venv/` (Linux/WSL). Activate it before running any commands:

```bash
source .venv/bin/activate
```

The old `dbt_venv/` was created on Windows and does not work on WSL — ignore it.

## dbt Workflow

dbt requires `--profiles-dir .dbt` because the connection config is not in the default `~/.dbt/` location.

Run steps in this order:

```bash
source .venv/bin/activate
dbt deps --profiles-dir .dbt        # Install packages (dbt_utils) — required after clone/CI
dbt seed --profiles-dir .dbt        # Load CSVs from seeds/ into PostgreSQL
dbt run --profiles-dir .dbt         # Execute SQL models (staging → intermediate → marts)
dbt test --profiles-dir .dbt        # Validate column constraints (unique, not_null)
```

To run a specific model: `dbt run --profiles-dir .dbt --select stg_bbr__players`

## Database Connection

PostgreSQL connection in `.dbt/profiles.yml` reads from env vars with localhost defaults:
- `DBT_HOST` (default `localhost`), `DBT_PORT` (`5432`), `DBT_DBNAME` (`nba`)
- `DBT_USER` (`postgres`), `DBT_PASSWORD` (`postgres`)

The database must be running locally before any dbt commands. On WSL:

```bash
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE nba;"   # only needed once
```

Alternatively, start Postgres via Docker (uses the same env vars):

```bash
docker compose up -d postgres
```

## Data Sources

All data comes from **Basketball Reference**. Scrapers are Python scripts in `src/scraping/`, each writing one CSV to `seeds/`. Run them all via the orchestrator:

```bash
source .venv/bin/activate
cd src/scraping
python run_all.py        # runs every scraper in dependency order
```

Shared Selenium/parsing helpers live in `src/scraping/common/`. All scrapers use Selenium (Chrome headless) because Basketball Reference blocks plain HTTP requests. `players` must run before `player_gamelogs` (gamelogs need `bbr_id` from `players.csv`).

| Scraper | Output seed |
|---|---|
| `players.py` | `players.csv` |
| `stats.py` | `players_stats.csv` |
| `advanced_stats.py` | `players_advanced_stats.csv` |
| `teams.py` | `team.csv` |
| `contracts.py` | `contracts.csv` |
| `draft.py` | `draft.csv` |
| `player_gamelogs.py` | `player_gamelogs.csv` |
| `box_scores.py` | `box_scores.csv` |

### FantasyGM league scraper (separate source)

`fantasy_gm.py` is **not** part of `run_all.py` and does **not** use Basketball
Reference. It pulls the "Bandeja de 3" fantasy league from FantasyGM
(`bskt.fantasygm.com.br`), which exposes an internal JSON API — Selenium is used
only to log in; the rest is plain `requests`. See runbook #27 for the API/auth
details. Credentials come from env vars (never hard-coded):

```bash
export FGM_EMAIL="…"; export FGM_PASS="…"
python src/scraping/fantasy_gm.py
```

Outputs (all gitignored except the two regenerated manual seeds): `fantasy_rosters.csv`,
`fantasy_franchises.csv`, `fantasy_standings.csv`, `fantasy_draft_class.csv`,
`fantasy_draft_picks.csv`, `fantasy_trades.csv`, `fantasy_injuries.csv`, and it
regenerates the versioned `my_roster.csv` + `fantasy_contracts.csv` from the live
roster. Calendar/matchups/auction endpoints exist but stay empty until the season
schedule is drawn.

## Orchestration (Dagster)

Dagster (`orchestration/`) schedules the scraping + dbt pipeline. The UI needs a dbt manifest, so compile first:

```bash
source .venv/bin/activate
dbt compile --profiles-dir .dbt        # generates target/manifest.json (required by dagster-dbt)
dagster dev -f orchestration/definitions.py   # UI at http://localhost:3000
```

Dagster deps are separate: `pip install dagster dagster-dbt dagster-webserver` (also in requirements.txt).

Jobs: `nba_pipeline` (weekly static scrape + dbt build), `historical_backfill` (game logs/advanced stats partitioned by season), `dbt_build` (triggered by the `csv_quality_sensor`, which validates CSV row counts before dbt runs).

## SQL Column Naming

Basketball Reference CSV columns with special characters **must be double-quoted** in SQL:

- `"FG%"`, `"3P"`, `"3PA"`, `"3P%"`, `"2P"`, `"2PA"`, `"2P%"`, `"eFG%"`, `"FT%"` — percentages and special chars

BBR also inserts repeated header rows in tables. Always filter them out in SQL:
```sql
where trim("Player") != 'Player'
```

## Model Layer Conventions

- `stg_bbr__*` — staging, in `models/staging/bbr/`; read seed CSVs via `{{ ref('seed_name') }}`; sources in `_bbr__sources.yml`
- `int_*` — intermediate (dedup, season totals), in `models/intermediate/`
- `dim_*` / `fct_*` — marts, in `models/marts/dimensions/` and `models/marts/facts/`

## CSV Seeds

Seeds live in `seeds/`, written directly by the scrapers in `src/scraping/`. BBR's ragged rows and repeated header rows are handled in the scrapers and filtered in SQL (see SQL Column Naming) — there is no separate repair script.

## Dashboard (Streamlit)

**Single entrypoint** (the old `fantasy_gm_tool.py` was merged into it — Rodada 6):

```bash
source .venv/bin/activate
streamlit run dashboard/app.py        # http://localhost:8501
```

Two tab families: seed-based tabs (Meu Time, Predicts, Guerra, FA, Draft, Liga,
Salários — always work, powered by `dashboard/fantasy_engine.py` + `fa_draft_engine.py`
+ `predicts.py`, shared helpers in `ui_common.py`) and dbt-mart tabs (NBA Médias/Valor,
College, Scouting, Comps — need Postgres; show a warning when it's down, never a
stacktrace). Headless smoke-test of every tab (run after touching the dashboard):

```bash
python dashboard/test_app_smoke.py    # AppTest; exit 0 = green
```

## Documentation

Project docs live in `docs/`:
- `desafios_e_solucoes.md` — troubleshooting runbook + design-decision log (D-01…). Check here before debugging known issues (Cloudflare blocking, synthetic `bbr_id`, PG type inference); add new resolved problems here.
- `modelo_de_dados.md`, `auditoria_modelo.md`, `dicas_otimizacoes.md` — data model, audit results, optimization backlog.
- `docs/fantasy/` — "Bandeja de 3" fantasy feature: design docs + estado (`ESTADO.md`), estratégia de offseason (`09_...md`), pendências de decisão (`PENDENCIAS_VALIDACAO.md`). Models live in `models/marts/fantasy/` and the decision engine in `dashboard/`.

CI (`.github/workflows/ci.yml`) runs `dbt seed → compile → run → test` on every PR; keep it green.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
