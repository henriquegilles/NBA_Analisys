"""
Assets do Dagster para o pipeline NBA Analytics.

Estrutura de dependências:
    scrape_players  ─┐
    scrape_stats    ─┼─► nba_dbt_assets (todos os modelos dbt em sequência)
    scrape_teams    ─┤
    scrape_contracts─┘

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

from dagster import AssetExecutionContext, asset
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

# ── Caminhos ─────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.parent
SCRAPING_DIR = PROJECT_DIR / "src" / "scraping"
VENV_PYTHON = PROJECT_DIR / ".venv" / "bin" / "python"

dbt_project = DbtProject(
    project_dir=PROJECT_DIR,
    packaged_project_dir=PROJECT_DIR,
)

# ── Assets de scraping ────────────────────────────────────────────────────────


def _run_scraper(script: str) -> None:
    """Executa um script de scraping como subprocess usando o .venv do projeto."""
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
        print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(
            f"Scraper {script} falhou (exit {result.returncode}):\n{result.stderr}"
        )


@asset(
    group_name="scraping",
    description="Extrai roster de jogadores do Basketball Reference → seeds/players.csv",
    kinds={"python", "selenium"},
)
def scrape_players(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de jogadores (BBR per-game page)...")
    _run_scraper("players.py")
    context.log.info("seeds/players.csv atualizado.")


@asset(
    group_name="scraping",
    description="Extrai estatísticas per-game do BBR → seeds/players_stats.csv",
    kinds={"python", "selenium"},
)
def scrape_stats(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de estatísticas (BBR per-game stats)...")
    _run_scraper("stats.py")
    context.log.info("seeds/players_stats.csv atualizado.")


@asset(
    group_name="scraping",
    description="Extrai histórico de franquias do BBR → seeds/team.csv",
    kinds={"python", "selenium"},
)
def scrape_teams(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de times (BBR teams page)...")
    _run_scraper("teams.py")
    context.log.info("seeds/team.csv atualizado.")


@asset(
    group_name="scraping",
    description="Extrai contratos dos jogadores do BBR → seeds/contracts.csv",
    kinds={"python", "selenium"},
)
def scrape_contracts(context: AssetExecutionContext) -> None:
    context.log.info("Iniciando scraping de contratos (BBR contracts page)...")
    _run_scraper("contracts.py")
    context.log.info("seeds/contracts.csv atualizado.")


# ── Assets dbt ────────────────────────────────────────────────────────────────
# O decorador @dbt_assets lê o manifest.json gerado por `dbt compile`
# e cria um asset Dagster para cada modelo dbt automaticamente.
# As dependências entre modelos (via ref()) são preservadas no grafo do Dagster.


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    # Cada scraping asset alimenta os seeds; seeds alimentam os modelos dbt.
    # Declaramos a dependência aqui para o Dagster montar o grafo completo.
    deps=[scrape_players, scrape_stats, scrape_teams, scrape_contracts],
)
def nba_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    Todos os modelos dbt do projeto, executados em ordem pelo DAG do dbt.
    Equivalente a: dbt seed && dbt run && dbt test
    """
    yield from dbt.cli(["build"], context=context).stream()
