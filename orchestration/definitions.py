"""
Dagster Definitions — ponto de entrada do projeto de orquestração.

Para iniciar a UI do Dagster:
    source .venv/bin/activate
    dbt compile --profiles-dir .dbt          # gera o manifest.json
    dagster dev -f orchestration/definitions.py

Acesse: http://localhost:3000

Jobs disponíveis:
  • nba_pipeline          — roda todo semana: scraping estático + dbt build
  • historical_backfill   — backfill histórico de game logs e advanced stats por season
  • dbt_build             — apenas o dbt build (disparado pelo csv_quality_sensor)

Sensor:
  • csv_quality_sensor    — valida contagem de linhas antes de disparar dbt build
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
    # particionados — não incluir em jobs não-particionados:
    scrape_advanced_stats,
    scrape_player_gamelogs,
)

PROJECT_DIR = Path(__file__).parent.parent

# ── Recurso dbt ──────────────────────────────────────────────────────────────
dbt_resource = DbtCliResource(
    project_dir=str(PROJECT_DIR),
    profiles_dir=str(PROJECT_DIR / ".dbt"),
    global_config_flags=["--no-use-colors"],
)

# ── Job semanal — ativos estáticos (não particionados) + dbt ─────────────────
# scrape_advanced_stats e scrape_player_gamelogs foram movidos para
# historical_backfill_job (particionado por season) — use-o para backfill
# e rode manualmente o partition "2025-26" para a temporada atual.
nba_pipeline_job = define_asset_job(
    name="nba_pipeline",
    description="Scraping BBR (ativos estáticos) + dbt seed/run/test completo",
    selection=[
        scrape_players,
        scrape_stats,
        scrape_teams,
        scrape_contracts,
        scrape_draft,
        nba_dbt_assets,
    ],
)

# ── Schedule — toda segunda-feira às 06:00 ───────────────────────────────────
nba_weekly_schedule = ScheduleDefinition(
    job=nba_pipeline_job,
    cron_schedule="0 6 * * 1",
    name="nba_weekly_monday",
    description="Atualiza dados da NBA toda segunda-feira às 06:00",
)

# ── Definitions ───────────────────────────────────────────────────────────────
defs = Definitions(
    assets=[
        scrape_players,
        scrape_stats,
        scrape_teams,
        scrape_contracts,
        scrape_draft,
        scrape_advanced_stats,    # particionado por SEASONS
        scrape_player_gamelogs,   # particionado por SEASONS
        nba_dbt_assets,
    ],
    resources={
        "dbt": dbt_resource,
    },
    jobs=[
        nba_pipeline_job,
        historical_backfill_job,  # backfill por season — use na UI para 2022-23..2025-26
        dbt_build_job,            # disparado pelo sensor após validação de CSV
    ],
    schedules=[nba_weekly_schedule],
    sensors=[csv_quality_sensor],
)
