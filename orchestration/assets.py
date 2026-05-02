"""
Assets do Dagster para o pipeline NBA Analytics.

Estrutura de dependências:
    scrape_players  ─┐
    scrape_stats    ─┼─► nba_dbt_assets (todos os modelos dbt em sequência)
    scrape_teams    ─┤
    scrape_contracts─┘
    scrape_advanced_stats
    scrape_draft
    scrape_player_gamelogs (deps: scrape_players)

Os assets de scraping produzem os CSVs em seeds/.
Os assets dbt são gerados automaticamente a partir do manifest do projeto dbt.

Para gerar o manifest antes de iniciar o Dagster:
    source .venv/bin/activate
    dbt compile --profiles-dir .dbt
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    Backoff,
    MetadataValue,
    RetryPolicy,
    asset,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

# ── Caminhos ─────────────────────────────────────────────────────────────────
PROJECT_DIR  = Path(__file__).parent.parent
SCRAPING_DIR = PROJECT_DIR / "src" / "scraping"
VENV_PYTHON  = PROJECT_DIR / ".venv" / "bin" / "python"

dbt_project = DbtProject(
    project_dir=PROJECT_DIR,
    packaged_project_dir=PROJECT_DIR,
)

# ── Retry policy para scrapers Selenium ──────────────────────────────────────
# BBR pode retornar rate-limit, timeout ou HTML diferente do esperado.
# 3 tentativas com backoff exponencial (60s → 120s → 240s) cobrem a maioria
# dos casos transitórios sem travar o pipeline por horas.
SCRAPER_RETRY = RetryPolicy(
    max_retries=3,
    delay=60,
    backoff=Backoff.EXPONENTIAL,
)


# ── Helper ───────────────────────────────────────────────────────────────────

def _run_scraper(script: str, context: AssetExecutionContext) -> dict:
    """
    Executa um script de scraping como subprocess usando o .venv do projeto.
    Retorna metadados básicos (linhas do CSV gerado) para observabilidade.
    """
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    result = subprocess.run(
        [python, script],
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
            f"Scraper {script} falhou (exit {result.returncode}):\n{result.stderr}"
        )
    return {"stdout": result.stdout}


def _csv_row_count(seed_name: str) -> int | None:
    """Conta linhas do CSV gerado (excluindo header). Retorna None se não existir."""
    path = PROJECT_DIR / "seeds" / seed_name
    if not path.exists():
        return None
    with open(path) as f:
        return max(0, sum(1 for _ in f) - 1)


# ── Assets de scraping ────────────────────────────────────────────────────────

@asset(
    group_name="scraping",
    description="Extrai roster de jogadores do Basketball Reference → seeds/players.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_players(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de jogadores (BBR per-game page)...")
    _run_scraper("players.py", context)
    rows = _csv_row_count("players.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"seeds/players.csv atualizado — {rows} linhas.")


@asset(
    group_name="scraping",
    description="Extrai estatísticas per-game do BBR → seeds/players_stats.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_stats(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de estatísticas (BBR per-game stats)...")
    _run_scraper("stats.py", context)
    rows = _csv_row_count("players_stats.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"seeds/players_stats.csv atualizado — {rows} linhas.")


@asset(
    group_name="scraping",
    description="Extrai histórico de franquias do BBR → seeds/team.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_teams(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de times (BBR teams page)...")
    _run_scraper("teams.py", context)
    rows = _csv_row_count("team.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"seeds/team.csv atualizado — {rows} linhas.")


@asset(
    group_name="scraping",
    description="Extrai contratos dos jogadores do BBR → seeds/contracts.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_contracts(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de contratos (BBR contracts page)...")
    _run_scraper("contracts.py", context)
    rows = _csv_row_count("contracts.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"seeds/contracts.csv atualizado — {rows} linhas.")


@asset(
    group_name="scraping",
    description="Extrai advanced stats (regular + playoffs) do BBR → seeds/players_advanced_stats.csv",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_advanced_stats(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de advanced stats (BBR regular season + playoffs)...")
    _run_scraper("advanced_stats.py", context)
    rows = _csv_row_count("players_advanced_stats.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"seeds/players_advanced_stats.csv atualizado — {rows} linhas.")


@asset(
    group_name="scraping",
    description="Extrai game logs por jogador do BBR → seeds/player_gamelogs.csv",
    kinds={"python", "selenium"},
    deps=[scrape_players],
    retry_policy=SCRAPER_RETRY,
)
def scrape_player_gamelogs(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de game logs (BBR, ~500 jogadores, sessão única)...")
    _run_scraper("player_gamelogs.py", context)
    rows = _csv_row_count("player_gamelogs.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"seeds/player_gamelogs.csv atualizado — {rows} linhas.")


@asset(
    group_name="scraping",
    description="Extrai 40 anos de Draft NBA do BBR → seeds/draft.csv (sessão única do browser)",
    kinds={"python", "selenium"},
    retry_policy=SCRAPER_RETRY,
)
def scrape_draft(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de Draft (BBR, 40 classes, sessão única)...")
    _run_scraper("draft.py", context)
    rows = _csv_row_count("draft.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0)})
    context.log.info(f"seeds/draft.csv atualizado — {rows} linhas.")


# ── Assets dbt ────────────────────────────────────────────────────────────────
# O decorador @dbt_assets lê o manifest.json gerado por `dbt compile`
# e cria um asset Dagster para cada modelo dbt automaticamente.
# As dependências entre modelos (via ref()) são preservadas no grafo do Dagster.

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
    Todos os modelos dbt do projeto, executados em ordem pelo DAG do dbt.
    Equivalente a: dbt seed && dbt run && dbt test
    """
    yield from dbt.cli(["build"], context=context).stream()
