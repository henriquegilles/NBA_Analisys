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

# ── Caminhos ─────────────────────────────────────────────────────────────────
PROJECT_DIR  = Path(__file__).parent.parent
SCRAPING_DIR = PROJECT_DIR / "src" / "scraping"
VENV_PYTHON  = PROJECT_DIR / ".venv" / "bin" / "python"

dbt_project = DbtProject(
    project_dir=PROJECT_DIR,
    packaged_project_dir=PROJECT_DIR,
)

# ── Partições sazonais ────────────────────────────────────────────────────────
# Scrapers multi-temporada (game logs, advanced stats) são particionados por season
# para permitir backfills históricos e monitorar quais temporadas foram carregadas.
# Adicionar uma nova season: basta estender a lista abaixo.
SEASONS = StaticPartitionsDefinition([
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
])

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

def _run_scraper(script: str, context: AssetExecutionContext, extra_args: list[str] | None = None) -> dict:
    """
    Executa um script de scraping como subprocess usando o .venv do projeto.
    extra_args são passados diretamente ao script (ex: ["--season", "2025-26"]).
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
    partitions_def=SEASONS,
)
def scrape_advanced_stats(context: AssetExecutionContext) -> None:
    season = context.partition_key
    context.log.info(f"Iniciando scraping de advanced stats — temporada {season}...")
    _run_scraper("advanced_stats.py", context, extra_args=["--season", season])
    rows = _csv_row_count("players_advanced_stats.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0), "season": MetadataValue.text(season)})
    context.log.info(f"seeds/players_advanced_stats.csv atualizado — {rows} linhas.")


@asset(
    group_name="scraping",
    description="Extrai game logs por jogador do BBR → seeds/player_gamelogs.csv",
    kinds={"python", "selenium"},
    deps=[scrape_players],
    retry_policy=SCRAPER_RETRY,
    partitions_def=SEASONS,
)
def scrape_player_gamelogs(context: AssetExecutionContext) -> None:
    season = context.partition_key
    context.log.info(f"Iniciando scraping de game logs — temporada {season} (~500 jogadores, sessão única)...")
    _run_scraper("player_gamelogs.py", context, extra_args=["--season", season])
    rows = _csv_row_count("player_gamelogs.csv")
    context.add_output_metadata({"row_count": MetadataValue.int(rows or 0), "season": MetadataValue.text(season)})
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


# ── Sensor de qualidade de CSV ───────────────────────────────────────────────

# Limites mínimos de linhas para cada seed. Se um CSV ficar abaixo do threshold,
# o sensor bloqueia o pipeline emitindo um SkipReason em vez de deixar dbt rodar
# com dados incompletos (ex: scraper truncou o arquivo silenciosamente).
_CSV_THRESHOLDS: dict[str, int] = {
    "players.csv":                400,  # ~500 jogadores ativos por temporada
    "players_stats.csv":          400,
    "contracts.csv":              300,  # alguns jogadores sem contrato registrado
    "team.csv":                    28,  # 30 franquias, mas 2 expansões recentes podem faltar
    "players_advanced_stats.csv": 400,
    "draft.csv":                  500,  # 40 anos × ~60 picks
    "player_gamelogs.csv":       1000,  # muitas linhas por temporada
}

# Job disparado pelo sensor quando todos os CSVs passam na validação
dbt_build_job = define_asset_job(
    name="dbt_build_job",
    selection=[nba_dbt_assets],
    description="Executa dbt build após validação de qualidade dos CSVs.",
)


@sensor(
    job=dbt_build_job,
    description="Valida contagem de linhas dos CSVs antes de disparar o dbt build.",
    minimum_interval_seconds=300,  # verifica a cada 5 min no máximo
)
def csv_quality_sensor(context: SensorEvaluationContext) -> SensorResult:
    """
    Lê cada seed CSV e verifica se passou do threshold mínimo de linhas.
    Se qualquer arquivo estiver abaixo do limite, emite SkipReason com detalhes.
    Isso previne que um scraper com falha silenciosa invalide os modelos dbt.
    """
    failures: list[str] = []
    missing: list[str] = []

    for filename, threshold in _CSV_THRESHOLDS.items():
        path = PROJECT_DIR / "seeds" / filename
        if not path.exists():
            missing.append(filename)
            continue
        rows = _csv_row_count(filename)
        if rows is not None and rows < threshold:
            failures.append(f"{filename}: {rows} linhas (mínimo: {threshold})")

    if missing:
        return SensorResult(
            skip_reason=SkipReason(f"CSVs ausentes — scraping ainda não rodou: {', '.join(missing)}"),
        )

    if failures:
        return SensorResult(
            skip_reason=SkipReason(
                "CSVs abaixo do threshold mínimo — possível falha de scraping:\n"
                + "\n".join(f"  • {f}" for f in failures)
            ),
        )

    context.log.info("Todos os CSVs passaram na validação de qualidade. Disparando dbt build.")
    return SensorResult(run_requests=[RunRequest(run_key=None)])


# ── Jobs ─────────────────────────────────────────────────────────────────────

# Backfill histórico: roda todas as seasons para game logs + advanced stats.
# Uso: Dagster UI → Jobs → historical_backfill_job → Launchpad → selecionar partições.
historical_backfill_job = define_asset_job(
    name="historical_backfill_job",
    selection=[scrape_player_gamelogs, scrape_advanced_stats],
    description="Backfill histórico de game logs e advanced stats por temporada (2022-23 → 2025-26).",
    partitions_def=SEASONS,
)
