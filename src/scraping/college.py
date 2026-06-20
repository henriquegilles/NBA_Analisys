"""
Scraper: College Basketball Reference — player-season history (college_player_seasons.csv)

Backbone of the fantasy Domínio B (scouting de draft). Collects multi-season
college stats by **school × season** (decision D-27): each school-season page
lists every player on the roster, so one request covers ~14 players plus the
team's strength-of-schedule. Per-player career is reassembled downstream in dbt
by `cbb_id`.

Unlike the NBA scrapers we parse cells by their `data-stat` attribute instead of
`pd.read_html`: the data-stat names are already SQL-safe (pts_per_min, ts_pct…),
and the player cell's <a href> gives a stable `cbb_id` (URL slug) — far more
robust for the college→NBA bridge than matching on names.

Output:  seeds/college_player_seasons.csv  (grão: jogador × temporada de college)

URL:     sports-reference.com/cbb/schools/{school}/men/{season}.html
         (season = ano FINAL: 2019 = temporada 2018-19)

Tables used (see docs/fantasy/03_dominio_b_scouting.md §7):
  players_per_min  — per-40-min 6-cat + pos + games + minutes (D-10, já pronto)
  players_advanced — ts_pct, usg_pct, per, bpm/obpm/dbpm, ws
  roster           — class (Fr/So/Jr/Sr, proxy de idade D-26), height, weight, rsci
  meta block       — team SOS / SRS

Run standalone (multi-season historical backfill, NOT part of run_all.py):
    source .venv/bin/activate
    cd src/scraping
    python college.py                 # full configured scope
    python college.py --max-pages 4   # smoke test
"""

import argparse
import os
import re
import time

import pandas as pd
from bs4 import BeautifulSoup

from common.browser import fetch_page
from common.parsing import uncomment_tables

# --- Scope (D-27). Starter slice of reliable NBA-feeder programs × recent
# seasons. Scale the backbone later by editing these two constants. ---
SCHOOLS = ["duke", "kentucky", "kansas", "north-carolina", "ucla", "gonzaga"]
SEASONS = list(range(2016, 2026))  # 2015-16 … 2024-25 (season = final year)

OUTPUT = os.path.join(
    os.path.dirname(__file__), "../../seeds/college_player_seasons.csv"
)

# Per-40 and advanced fields pulled by data-stat (already SQL-safe).
PER_MIN_STATS = [
    "pos", "games", "games_started", "mp",
    "fg3_per_min", "fg3_pct", "ft_pct", "efg_pct",
    "trb_per_min", "ast_per_min", "stl_per_min", "blk_per_min",
    "tov_per_min", "pts_per_min",
]
ADVANCED_STATS = [
    "per", "ts_pct", "usg_pct", "ws", "obpm", "dbpm", "bpm",
]
ROSTER_STATS = ["class", "height", "weight", "rsci"]

# Final column order for the seed.
OUTPUT_COLS = (
    ["cbb_id", "player", "school", "season", "conf_abbr"]
    + ROSTER_STATS
    + PER_MIN_STATS
    + ADVANCED_STATS
    + ["team_sos", "team_srs"]
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape College Basketball Reference")
    parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Cap on school-season pages to fetch (smoke test).",
    )
    return parser.parse_args()


def _season_label(season: int) -> str:
    """2019 → '2018-19'."""
    return f"{season - 1}-{str(season)[2:]}"


def _cbb_id_from_cell(cell) -> str | None:
    """Extract the player URL slug (e.g. 'zion-williamson-1') from a name cell."""
    link = cell.find("a") if cell else None
    if not link or not link.get("href"):
        return None
    m = re.search(r"/cbb/players/([^.]+)\.html", link["href"])
    return m.group(1) if m else None


def _parse_table(soup: BeautifulSoup, table_id: str, name_stat: str, stats: list[str]):
    """
    Return {cbb_id: {stat: value, ...}} for one stats table, keyed by player slug.
    Rows without a player link (repeated headers, totals) are skipped.
    """
    table = soup.find("table", {"id": table_id})
    if table is None or table.find("tbody") is None:
        return {}

    out = {}
    for tr in table.find("tbody").find_all("tr"):
        if "thead" in (tr.get("class") or []):
            continue
        name_cell = tr.find(attrs={"data-stat": name_stat})
        cbb_id = _cbb_id_from_cell(name_cell)
        if cbb_id is None:
            continue
        row = {"player": name_cell.get_text(strip=True)}
        # conference lives on the per-min/advanced tables (player pages); on the
        # school-season page it's implied, so grab it if present.
        for stat in stats + ["conf_abbr"]:
            cell = tr.find(attrs={"data-stat": stat})
            row[stat] = cell.get_text(strip=True) if cell else None
        out[cbb_id] = row
    return out


def _parse_team_context(soup: BeautifulSoup) -> dict:
    """Pull team SOS / SRS from the meta block (team-level, not in player tables)."""
    info = soup.find("div", {"id": "info"}) or soup.find("div", {"id": "meta"})
    text = info.get_text(" ", strip=True) if info else ""
    out = {}
    for key, col in [("SOS", "team_sos"), ("SRS", "team_srs")]:
        m = re.search(rf"{key}\s*:?\s*(-?[\d.]+)", text)
        out[col] = m.group(1) if m else None
    return out


def _scrape_one(school: str, season: int) -> pd.DataFrame:
    url = f"https://www.sports-reference.com/cbb/schools/{school}/men/{season}.html"
    driver = fetch_page(url)
    soup = uncomment_tables(BeautifulSoup(driver.page_source, "lxml"))
    driver.quit()

    per_min = _parse_table(soup, "players_per_min", "name_display", PER_MIN_STATS)
    advanced = _parse_table(soup, "players_advanced", "name_display", ADVANCED_STATS)
    roster = _parse_table(soup, "roster", "player", ROSTER_STATS)
    team_ctx = _parse_team_context(soup)

    if not per_min:
        raise ValueError(f"No players_per_min table for {school} {season}")

    rows = []
    for cbb_id, base in per_min.items():
        row = {"cbb_id": cbb_id, "school": school, "season": _season_label(season)}
        row.update(base)
        row.update({k: v for k, v in advanced.get(cbb_id, {}).items() if k != "player"})
        row.update({k: v for k, v in roster.get(cbb_id, {}).items() if k != "player"})
        row.update(team_ctx)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.reindex(columns=OUTPUT_COLS)


def scrape() -> pd.DataFrame:
    args = _parse_args()
    targets = [(s, y) for s in SCHOOLS for y in SEASONS]
    if args.max_pages:
        targets = targets[: args.max_pages]

    frames = []
    for i, (school, season) in enumerate(targets, 1):
        print(f"  [{i}/{len(targets)}] {school} {_season_label(season)}...")
        try:
            df = _scrape_one(school, season)
            frames.append(df)
            print(f"    → {len(df)} players")
        except ValueError as exc:
            print(f"  WARNING: {exc} — skipping")
        time.sleep(1)  # be polite between pages

    if not frames:
        raise RuntimeError("No college seasons scraped — all pages failed.")

    return pd.concat(frames, ignore_index=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} player-seasons → {out}")


if __name__ == "__main__":
    main()
