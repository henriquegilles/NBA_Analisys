"""
Dagster assets for the NBA Analytics pipeline.

Dependency structure:
    scrape_players  ─┐
    scrape_stats    ─┼─► nba_dbt_assets (all dbt models in sequence)
    scrape_teams    ─┤
    scrape_contracts─┘
    scrape_advanced_stats
    scrape_draft
    scrape_player_gamelogs (deps: scrape_players)

The scraping assets write the CSVs to dbt/seeds/.
The dbt assets are generated automatically from the dbt project manifest.

To generate the manifest before starting Dagster:
    cd dbt
    uv run dbt compile
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Backoff,
    MetadataValue,
    RetryPolicy,
    RunRequest,
    SensorEvaluationContext,
    SensorResult,
    SkipReason,
    StaticPartitionsDefinition,
    asset,
    define_asset_job,
    sensor,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_DIR  = Path(__file__).parent.parent
SCRAPING_DIR = PROJECT_DIR / "src" / "scraping"
VENV_PYTHON  = PROJECT_DIR / ".venv" / "bin" / "python"

dbt_project = DbtProject(
    project_dir=PROJECT_DIR / "dbt",
    packaged_project_dir=PROJECT_DIR / "dbt",
)

# ── Season partitions ─────────────────────────────────────────────────────────
# Multi-season scrapers (game logs, advanced stats) are partitioned by season
# to enable historical backfills and track which seasons have been loaded.
# To add a new season: just extend the list below.
SEASONS = StaticPartitionsDefinition([
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
])

# ── Retry policy for Selenium scrapers ───────────────────────────────────────
# BBR may return rate limits, timeouts, or unexpected HTML.
# 3 attempts with exponential backoff (60s → 120s → 240s) cover most
# transient failures without stalling the pipeline for hours.
SCRAPER_RETRY = RetryPolicy(
    max_retries=3,
    delay=60,
    backoff=Backoff.EXPONENTIAL,
)


# ── Helper ───────────────────────────────────────────────────────────────────

def _run_scraper(script: str, context: AssetExecutionContext, extra_args: list[str] | None = None) -> dict:
    """
    Run a scraping script as a subprocess using the project's .venv.
    extra_args are passed straight to the script (e.g. ["--season", "2025-26"]).
    """
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    result = subprocess.run(
        [python, script, *(extra_args or [])],
        cwd=str(SCRAPING_DIR),
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(SCRAPING_DIR),
        },
    )
    if result.stdout:
        context.log.info(result.stdout.strip())
    if result.returncode != 0:
        context.log.error(result.stderr.strip())
        raise RuntimeError(
            f"Scraper {script} failed (exit {result.returncode}):\n{result.stderr}"
        )
    return {"stdout": result.stdout}


def _csv_row_count(seed_name: str) -> int | None:
    """Count rows in the generated CSV (excluding header). Returns None if missing."""
    path = PROJECT_DIR / "dbt" / "seeds" / seed_name
    if not path.exists():
        return None
    with open(path) as f:
        return max(0, sum(1 for _ in f) - 1)


# ── Scraping assets ───────────────────────────────────────────────────────────

@asset(
    group_name="scraping",
    description="Scrape the player roster from Basketball Reference → dbt/seeds/players.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_players(context: AssetExecutionContext) -> None:
    context.log.info("Starting player scraping (BBR per-game page)...")
    _run_scraper("players.py", context)
    rows = _csv_row_count("players.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"players.csv updated — {rows} rows.")


@asset(
    group_name="scraping",
    description="Scrape per-game stats from BBR → dbt/seeds/players_stats.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_stats(context: AssetExecutionContext) -> None:
    context.log.info("Starting stats scraping (BBR per-game stats)...")
    _run_scraper("stats.py", context)
    rows = _csv_row_count("players_stats.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"players_stats.csv updated — {rows} rows.")


@asset(
    group_name="scraping",
    description="Scrape franchise history from BBR → dbt/seeds/team.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_teams(context: AssetExecutionContext) -> None:
    context.log.info("Starting team scraping (BBR teams page)...")
    _run_scraper("teams.py", context)
    rows = _csv_row_count("team.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"team.csv updated — {rows} rows.")


@asset(
    group_name="scraping",
    description="Scrape player contracts from BBR → dbt/seeds/contracts.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_contracts(context: AssetExecutionContext) -> None:
    context.log.info("Starting contract scraping (BBR contracts page)...")
    _run_scraper("contracts.py", context)
    rows = _csv_row_count("contracts.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"contracts.csv updated — {rows} rows.")


@asset(
    group_name="scraping",
    description="Scrape advanced stats (regular + playoffs) from BBR → dbt/seeds/players_advanced_stats.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
    partitions_def=SEASONS,
)
def scrape_advanced_stats(context: AssetExecutionContext) -> None:
    season = context.partition_key
    context.log.info(f"Starting advanced stats scraping — season {season}...")
    _run_scraper("advanced_stats.py", context, extra_args=["--season", season])
    rows = _csv_row_count("players_advanced_stats.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0), "season": MetadataValue.text(season)})
    context.log.info(f"players_advanced_stats.csv updated — {rows} rows.")


@asset(
    group_name="scraping",
    description="Scrape per-player game logs from BBR → dbt/seeds/player_gamelogs.csv",
    kinds={"python", "selenium"},
    deps=[scrape_players],
    retry_policy=SCRAPER_RETRY,
    partitions_def=SEASONS,
)
def scrape_player_gamelogs(context: AssetExecutionContext) -> None:
    season = context.partition_key
    context.log.info(f"Starting game log scraping — season {season} (~500 players, single session)...")
    _run_scraper("player_gamelogs.py", context, extra_args=["--season", season])
    rows = _csv_row_count("player_gamelogs.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0), "season": MetadataValue.text(season)})
    context.log.info(f"player_gamelogs.csv updated — {rows} rows.")


@asset(
    group_name="scraping",
    description="Scrape 40 years of NBA Draft data from BBR → dbt/seeds/draft.csv (single browser session)",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_draft(context: AssetExecutionContext) -> None:
    context.log.info("Starting draft scraping (BBR, 40 classes, single session)...")
    _run_scraper("draft.py", context)
    rows = _csv_row_count("draft.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"draft.csv updated — {rows} rows.")


# ── dbt assets ────────────────────────────────────────────────────────────────
# The @dbt_assets decorator reads the manifest.json generated by `dbt compile`
# and automatically creates a Dagster asset for each dbt model.
# Dependencies between models (via ref()) are preserved in the Dagster graph.

@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    deps=[
        scrape_players,
        scrape_stats,
        scrape_teams,
        scrape_contracts,
        scrape_advanced_stats,
        scrape_draft,
        scrape_player_gamelogs,
    ],
)
def nba_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    All dbt models in the project, executed in order by the dbt DAG.
    Equivalent to: dbt seed && dbt run && dbt test
    """
    yield from dbt.cli(["build"], context=context).stream()


# ── CSV quality sensor ───────────────────────────────────────────────────────

# Minimum row counts for each seed. If a CSV falls below its threshold,
# the sensor blocks the pipeline by emitting a SkipReason instead of letting
# dbt run with incomplete data (e.g. a scraper silently truncated the file).
_CSV_THRESHOLDS: dict[str, int] = {
    "players.csv":                400,  # ~500 active players per season
    "players_stats.csv":          400,
    "contracts.csv":              300,  # some players have no recorded contract
    "team.csv":                    28,  # 30 franchises, but 2 recent expansions may be missing
    "players_advanced_stats.csv": 400,
    "draft.csv":                  500,  # 40 years × ~60 picks
    "player_gamelogs.csv":       1000,  # many rows per season
}

# Job triggered by the sensor once every CSV passes validation
dbt_build_job = define_asset_job(
    name="dbt_build_job",
    selection=[nba_dbt_assets],
    description="Run dbt build after CSV quality validation.",
)


@sensor(
    job=dbt_build_job,
    description="Validate CSV row counts before triggering dbt build.",
    minimum_interval_seconds=300,  # check at most every 5 min
)
def csv_quality_sensor(context: SensorEvaluationContext) -> SensorResult:
    """
    Read each seed CSV and check that it clears the minimum row threshold.
    If any file is below the limit, emit a SkipReason with details.
    This prevents a silently failing scraper from invalidating the dbt models.
    """
    failures: list[str] = []
    missing: list[str] = []

    for filename, threshold in _CSV_THRESHOLDS.items():
        path = PROJECT_DIR / "dbt" / "seeds" / filename
        if not path.exists():
            missing.append(filename)
            continue
        rows = _csv_row_count(filename)
        if rows is not None and rows < threshold:
            failures.append(f"{filename}: {rows} rows (minimum: {threshold})")

    if missing:
        return SensorResult(
            skip_reason=SkipReason(f"Missing CSVs — scraping has not run yet: {', '.join(missing)}"),
        )

    if failures:
        return SensorResult(
            skip_reason=SkipReason(
                "CSVs below the minimum threshold — possible scraping failure:\n"
                + "\n".join(f"  • {f}" for f in failures)
            ),
        )

    context.log.info("All CSVs passed quality validation. Triggering dbt build.")
    return SensorResult(run_requests=[RunRequest(run_key=None)])


# ── Jobs ─────────────────────────────────────────────────────────────────────

# Historical backfill: runs every season for game logs + advanced stats.
# Usage: Dagster UI → Jobs → historical_backfill_job → Launchpad → select partitions.
historical_backfill_job = define_asset_job(
    name="historical_backfill_job",
    selection=[scrape_player_gamelogs, scrape_advanced_stats],
    description="Historical backfill of game logs and advanced stats by season (2022-23 → 2025-26).",
    partitions_def=SEASONS,
)
