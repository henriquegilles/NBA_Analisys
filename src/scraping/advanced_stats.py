"""
Scraper: BBR advanced stats — regular season + playoffs (players_advanced_stats.csv)

Scrapes the BBR advanced stats table for both season types and combines
them into a single CSV with `season` and `season_type` columns.

Output:  seeds/players_advanced_stats.csv

URLs:
  Regular season: basketball-reference.com/leagues/NBA_{SEASON}_advanced.html
  Playoffs:       basketball-reference.com/playoffs/NBA_{SEASON}_advanced.html

Table ID on both pages: advanced_stats
"""

import os
import pandas as pd
from bs4 import BeautifulSoup

from common.browser import fetch_page
from common.parsing import uncomment_tables, get_table

SEASON = os.getenv("BBR_SEASON", "2026")

# e.g. SEASON=2026 → "2025-26"
_season_start = int(SEASON) - 1
_season_end = str(SEASON)[2:]
SEASON_LABEL = f"{_season_start}-{_season_end}"

URLS = {
    "regular": f"https://www.basketball-reference.com/leagues/NBA_{SEASON}_advanced.html",
    "playoffs": f"https://www.basketball-reference.com/playoffs/NBA_{SEASON}_advanced.html",
}

OUTPUT = os.path.join(os.path.dirname(__file__), "../../seeds/players_advanced_stats.csv")

# BBR uses different table IDs for regular season vs playoffs pages
TABLE_IDS = {
    "regular":  "advanced",
    "playoffs": "advanced_stats",
}

# BBR advanced stats columns with special characters or SQL-unsafe names.
RENAME = {
    "TS%":   "ts_pct",
    "3PAr":  "three_p_ar",
    "FTr":   "ftr",
    "ORB%":  "orb_pct",
    "DRB%":  "drb_pct",
    "TRB%":  "trb_pct",
    "AST%":  "ast_pct",
    "STL%":  "stl_pct",
    "BLK%":  "blk_pct",
    "TOV%":  "tov_pct",
    "USG%":  "usg_pct",
    "WS/48": "ws_per_48",
}

DROP = ["Rk", "Awards"]


def _scrape_one(url: str, season_type: str) -> pd.DataFrame:
    driver = fetch_page(url)
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

    soup = uncomment_tables(soup)
    table = get_table(soup, TABLE_IDS[season_type])

    df = pd.read_html(str(table))[0]

    # Drop multi-level header columns (BBR sometimes nests headers)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(-1)

    df = df[df["Player"].notna()]
    df = df[df["Player"].str.strip() != "Player"]
    df = df[df["Player"].str.strip() != "League Average"]

    df = df.drop(columns=[c for c in DROP if c in df.columns])
    df = df.rename(columns=RENAME)

    df["season"] = SEASON_LABEL
    df["season_type"] = season_type

    return df.reset_index(drop=True)


def scrape() -> pd.DataFrame:
    frames = []
    for season_type, url in URLS.items():
        print(f"  Scraping {season_type} advanced stats...")
        try:
            df = _scrape_one(url, season_type)
            frames.append(df)
            print(f"    → {len(df)} rows")
        except ValueError as exc:
            # Playoffs page may not exist if playoffs haven't started
            print(f"  WARNING: {exc} — skipping {season_type}")

    if not frames:
        raise RuntimeError("No advanced stats scraped — both URLs failed.")

    return pd.concat(frames, ignore_index=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")


if __name__ == "__main__":
    main()
