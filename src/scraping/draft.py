"""
Scraper: BBR NBA Draft data — 40 seasons in a single browser session.
Output:  dbt/seeds/draft.csv

URL pattern: basketball-reference.com/draft/NBA_{year}.html
Table ID:    stats

Optimization strategy:
- Single Selenium session reused across all years (avoids Chrome startup
  overhead of ~20s per launch).
- 3-second sleep between page navigations (vs 8s for fresh sessions).
- Year range set via BBR_DRAFT_END (default 2025) going back 40 years.

Columns scraped per draft class:
    draft_year, round, pick, team, player_name, bbr_id, college,
    career_years, career_games, career_mp, career_pts,
    career_trb, career_ast, career_fg_pct, career_3p_pct,
    career_ft_pct, pg_mp, pg_pts, pg_trb, pg_ast,
    win_shares, ws_per_48, bpm, vorp
"""

import os
import re
import time

import pandas as pd
from bs4 import BeautifulSoup

from common.browser import build_driver
from common.parsing import uncomment_tables, get_table

END_YEAR   = int(os.getenv("BBR_DRAFT_END", "2025"))
NUM_YEARS  = int(os.getenv("BBR_DRAFT_YEARS", "40"))
START_YEAR = END_YEAR - NUM_YEARS + 1   # e.g. 1986 when END=2025, NUM=40

OUTPUT = os.path.join(os.path.dirname(__file__), "../../dbt/seeds/draft.csv")

TABLE_ID = "stats"

# Seconds between page navigations (much less than a fresh session needs).
NAV_SLEEP = 3

# We parse the draft `stats` table by `data-stat` instead of pd.read_html. The
# data-stat names are stable and SQL-safe, the player cell's <a href> gives the
# bbr_id slug directly, and — crucially — this is immune to BBR's two-level header
# shuffles (the old read_html+flatten broke when "Player" started flattening to
# "Round 1_Player" and percentages moved under a "Shooting" group — runbook #25).
# `round` is intentionally omitted: stg_bbr__draft derives it from the pick.
DATA_STATS = {
    "pick_overall": "pick",
    "team_id":      "team",
    "player":       "player_name",
    "college_name": "college",
    "seasons":      "career_years",
    "g":            "career_games",
    "mp":           "career_mp",
    "pts":          "career_pts",
    "trb":          "career_trb",
    "ast":          "career_ast",
    "fg_pct":       "career_fg_pct",
    "fg3_pct":      "career_3p_pct",
    "ft_pct":       "career_ft_pct",
    "mp_per_g":     "pg_mp",
    "pts_per_g":    "pg_pts",
    "trb_per_g":    "pg_trb",
    "ast_per_g":    "pg_ast",
    "ws":           "win_shares",
    "ws_per_48":    "ws_per_48",
    "bpm":          "bpm",
    "vorp":         "vorp",
}

OUTPUT_COLS = (
    ["draft_year", "pick", "team", "player_name", "bbr_id", "college"]
    + [c for c in DATA_STATS.values()
       if c not in ("pick", "team", "player_name", "college")]
)


def _parse_draft_page(driver, year: int) -> pd.DataFrame | None:
    """Navigate to the draft page for *year* and return a cleaned DataFrame."""
    url = f"https://www.basketball-reference.com/draft/NBA_{year}.html"
    driver.get(url)
    time.sleep(NAV_SLEEP)

    soup = uncomment_tables(BeautifulSoup(driver.page_source, "lxml"))

    try:
        table = get_table(soup, TABLE_ID)
    except ValueError:
        print(f"  WARNING: table #{TABLE_ID} not found for {year} — skipping")
        return None

    tbody = table.find("tbody")
    if tbody is None:
        print(f"  WARNING: no tbody for {year} — skipping")
        return None

    rows = []
    for tr in tbody.find_all("tr"):
        if "thead" in (tr.get("class") or []):
            continue  # repeated header rows
        name_cell = tr.find(attrs={"data-stat": "player"})
        link = name_cell.find("a") if name_cell else None
        # skip "Round 2" separators and undrafted/blank rows (no player link)
        if link is None or not link.get("href"):
            continue

        row = {"draft_year": year}
        for ds, col in DATA_STATS.items():
            cell = tr.find(attrs={"data-stat": ds})
            row[col] = cell.get_text(strip=True) if cell else None

        m = re.search(r"/players/[a-z]/([^.]+)\.html", link["href"])
        row["bbr_id"] = m.group(1) if m else None
        rows.append(row)

    if not rows:
        print(f"  WARNING: no player rows parsed for {year} — skipping")
        return None

    return pd.DataFrame(rows).reindex(columns=OUTPUT_COLS)


def scrape() -> pd.DataFrame:
    years = list(range(START_YEAR, END_YEAR + 1))
    print(f"Scraping {len(years)} draft classes: {years[0]}–{years[-1]}")

    driver = build_driver()
    frames = []
    try:
        for year in years:
            print(f"  → {year} ...", end=" ", flush=True)
            df = _parse_draft_page(driver, year)
            if df is not None:
                frames.append(df)
                print(f"{len(df)} picks")
            else:
                print("skipped")
    finally:
        driver.quit()

    if not frames:
        raise RuntimeError("No draft data scraped.")

    combined = pd.concat(frames, ignore_index=True)
    return combined


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} total picks ({START_YEAR}–{END_YEAR}) → {out}")


if __name__ == "__main__":
    main()
