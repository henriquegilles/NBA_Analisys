#!/usr/bin/env bash
# Demo bootstrap — runs the whole project from a fresh clone, WITHOUT scraping,
# using the consistent samples versioned in ci/sample_seeds/ (the same ones CI
# uses). Lets you see the pipeline + dashboard working in minutes.
#
# Real data comes from the scrapers (see README "Data Sources") — this is just
# the reproducible shortcut. Requires Postgres up (docker compose up -d postgres).
#
# Usage:
#   ./scripts/bootstrap_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Guard: don't overwrite real data already present (real gamelog ~4MB; demo ~184KB).
if [ -f dbt/seeds/player_gamelogs.csv ] && [ "$(wc -c < dbt/seeds/player_gamelogs.csv)" -gt 1000000 ]; then
  echo "⚠️  dbt/seeds/ already has real data (large player_gamelogs)."
  echo "    This script is for a fresh clone/demo and WOULD OVERWRITE your seeds."
  echo "    If you really want the sample data, run: BOOTSTRAP_FORCE=1 $0"
  [ "${BOOTSTRAP_FORCE:-0}" = "1" ] || exit 1
fi

echo "→ installing Python dependencies (uv sync)"
uv sync

echo "→ copying demo samples to dbt/seeds/"
cp ci/sample_seeds/*.csv dbt/seeds/

cd dbt

echo "→ dbt deps"
uv run dbt deps

echo "→ dbt build (seed + run + test) with sample data"
uv run dbt build

echo
echo "✓ Done. The demo warehouse is populated and tested."
echo "  Open the dashboard:  streamlit run dashboard/app.py   →  http://localhost:8501"
