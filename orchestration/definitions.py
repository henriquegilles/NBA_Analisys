"""
Dagster Definitions — entry point for the orchestration project.

To start the Dagster UI:
    cd dbt && uv run dbt compile             # generates manifest.json
    cd .. && uv run dagster dev -f orchestration/definitions.py

Open: http://localhost:3000

Available jobs:
  • nba_pipeline          — runs weekly: static scraping + dbt build
  • historical_backfill   — historical backfill of game logs and advanced stats by season
  • dbt_build             — dbt build only (triggered by csv_quality_sensor)

Sensor:
  • csv_quality_sensor    — validates row counts before triggering dbt build
"""

from __future__ import annotations

from pathlib import Path

from dagster import Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource

from orchestration.assets import (
    SEASONS,
    csv_quality_sensor,
    dbt_build_job,
    dbt_project,
    historical_backfill_job,
    nba_dbt_assets,
    scrape_contracts,
    scrape_draft,
    scrape_players,
    scrape_stats,
    scrape_teams,
    # partitioned — do not include in non-partitioned jobs:
    scrape_advanced_stats,
    scrape_player_gamelogs,
)

PROJECT_DIR = Path(__file__).parent.parent

# ── dbt resource ─────────────────────────────────────────────────────────────
dbt_resource = DbtCliResource(
    project_dir=str(PROJECT_DIR / "dbt"),
    profiles_dir=str(PROJECT_DIR / "dbt"),
    global_config_flags=["--no-use-colors"],
)

# ── Weekly job — static (non-partitioned) assets + dbt ───────────────────────
# scrape_advanced_stats and scrape_player_gamelogs were moved to
# historical_backfill_job (partitioned by season) — use it for backfills
# and manually run the "2025-26" partition for the current season.
nba_pipeline_job = define_asset_job(
    name="nba_pipeline",
    description="BBR scraping (static assets) + full dbt seed/run/test",
    selection=[
        scrape_players,
        scrape_stats,
        scrape_teams,
        scrape_contracts,
        scrape_draft,
        nba_dbt_assets,
    ],
)

# ── Schedule — every Monday at 06:00 ─────────────────────────────────────────
nba_weekly_schedule = ScheduleDefinition(
    job=nba_pipeline_job,
    cron_schedule="0 6 * * 1",
    name="nba_weekly_monday",
    description="Refresh NBA data every Monday at 06:00",
)

# ── Definitions ───────────────────────────────────────────────────────────────
defs = Definitions(
    assets=[
        scrape_players,
        scrape_stats,
        scrape_teams,
        scrape_contracts,
        scrape_draft,
        scrape_advanced_stats,    # partitioned by SEASONS
        scrape_player_gamelogs,   # partitioned by SEASONS
        nba_dbt_assets,
    ],
    resources={
        "dbt": dbt_resource,
    },
    jobs=[
        nba_pipeline_job,
        historical_backfill_job,  # backfill by season — use the UI for 2022-23..2025-26
        dbt_build_job,            # triggered by the sensor after CSV validation
    ],
    schedules=[nba_weekly_schedule],
    sensors=[csv_quality_sensor],
)
