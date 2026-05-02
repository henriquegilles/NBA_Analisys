"""
Dagster Definitions — ponto de entrada do projeto de orquestração.

Para iniciar a UI do Dagster:
    source .venv/bin/activate
    dbt compile --profiles-dir .dbt          # gera o manifest.json
    dagster dev -f orchestration/definitions.py

Acesse: http://localhost:3000
"""

from __future__ import annotations

import os
from pathlib import Path

from dagster import Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource

from orchestration.assets import (
    dbt_project,
    nba_dbt_assets,
    scrape_advanced_stats,
    scrape_contracts,
    scrape_draft,
    scrape_players,
    scrape_stats,
    scrape_teams,
)

PROJECT_DIR = Path(__file__).parent.parent

# ── Recurso dbt — configuração de conexão via env_var ────────────────────────
dbt_resource = DbtCliResource(
    project_dir=str(PROJECT_DIR),
    profiles_dir=str(PROJECT_DIR / ".dbt"),
    global_config_flags=["--no-use-colors"],
)

# ── Job — executa o pipeline completo ────────────────────────────────────────
nba_pipeline_job = define_asset_job(
    name="nba_pipeline",
    description="Scraping BBR + dbt seed/run/test completo",
    selection=[
        scrape_players,
        scrape_stats,
        scrape_teams,
        scrape_contracts,
        scrape_advanced_stats,
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

# ── Definitions — registro de todos os componentes ───────────────────────────
defs = Definitions(
    assets=[
        scrape_players,
        scrape_stats,
        scrape_teams,
        scrape_contracts,
        scrape_advanced_stats,
        scrape_draft,
        nba_dbt_assets,
    ],
    resources={
        "dbt": dbt_resource,
    },
    jobs=[nba_pipeline_job],
    schedules=[nba_weekly_schedule],
)
