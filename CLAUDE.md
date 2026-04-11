# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NBA basketball analytics portfolio project using dbt for SQL transformations, PostgreSQL as the data warehouse, and Jupyter notebooks for web scraping from Basketball Reference.

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
dbt seed --profiles-dir .dbt        # Load CSVs from basket_dbt/seeds/ into PostgreSQL
dbt run --profiles-dir .dbt         # Execute SQL models (staging layer)
dbt test --profiles-dir .dbt        # Validate column constraints (unique, not_null)
```

To run a specific model: `dbt run --profiles-dir .dbt --select stg_players`

## Database Connection

PostgreSQL connection is hardcoded in `.dbt/profiles.yml` (not using env vars):
- Host: `localhost`, port `5432`
- Database: `nba`
- User: `postgres`, password: `postgres`

The database must be running locally before any dbt commands. On WSL:

```bash
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE nba;"   # only needed once
```

## Data Sources

All data comes from **Basketball Reference**. Scrapers are Jupyter notebooks — run manually to refresh CSVs:

| Notebook | URL scraped | Output seed |
|---|---|---|
| `scraping/players/players.ipynb` | `basketball-reference.com/leagues/NBA_2025_per_game.html` | `players.csv` |
| `scraping/stats/stats.ipynb` | same page (full stats) | `players_stats.csv` |
| `scraping/teams/teams_scrap.ipynb` | `basketball-reference.com/teams/` | `team.csv` |
| `scraping/contracts/nba_contracts.ipynb` | `basketball-reference.com/contracts/players.html` | `contracts.csv` |

All scrapers use Selenium (Chrome headless) because Basketball Reference blocks plain HTTP requests.

## SQL Column Naming

Basketball Reference CSV columns with special characters **must be double-quoted** in SQL:

- `"FG%"`, `"3P"`, `"3PA"`, `"3P%"`, `"2P"`, `"2PA"`, `"2P%"`, `"eFG%"`, `"FT%"` — percentages and special chars

BBR also inserts repeated header rows in tables. Always filter them out in SQL:
```sql
where trim("Player") != 'Player'
```

## Model Layer Conventions

- `stg_*` — staging models read directly from seed CSVs via `{{ ref('seed_name') }}`
- Source definitions documented in `models/staging/_src__raw.yml`
- Enriched layer (dim_*, fact_*) does not exist yet — to be built once staging is stable

## CSV Seeds and fix_csv.py

Seeds live in `basket_dbt/seeds/`. If CSVs have malformed rows (ragged columns, blank lines), run the repair utility first:

```bash
python fix_csv.py basket_dbt/seeds/players.csv basket_dbt/seeds/players_stats.csv
```

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
