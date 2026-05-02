"""
Scraper: BBR NBA Draft data — 40 seasons in a single browser session.
Output:  seeds/draft.csv

URL pattern: basketball-reference.com/draft/NBA_{year}.html
Table ID:    stats

Optimization strategy:
- Single Selenium session reused across all years (avoids Chrome startup
  overhead of ~20s per launch).
- 3-second sleep between page navigations (vs 8s for fresh sessions).
- Year range set via BBR_DRAFT_END (default 2025) going back 40 years.

Columns scraped per draft class:
    draft_year, round, pick, team, player_name, college,
    career_years, career_games, career_mp, career_pts,
    career_trb, career_ast, career_fg_pct, career_3p_pct,
    career_ft_pct, pg_mp, pg_pts, pg_trb, pg_ast,
    win_shares, ws_per_48, bpm, vorp
"""

import os
import time

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver

from common.browser import build_driver
from common.parsing import uncomment_tables, get_table

END_YEAR   = int(os.getenv("BBR_DRAFT_END", "2025"))
NUM_YEARS  = int(os.getenv("BBR_DRAFT_YEARS", "40"))
START_YEAR = END_YEAR - NUM_YEARS + 1   # e.g. 1986 when END=2025, NUM=40

OUTPUT = os.path.join(os.path.dirname(__file__), "../../seeds/draft.csv")

TABLE_ID = "stats"

# Seconds between page navigations (much less than a fresh session needs).
NAV_SLEEP = 3

# Multi-level header: BBR groups columns as "Totals" and "Per Game".
# After flattening we rename duplicated/unsafe names to SQL-safe identifiers.
RENAME = {
    # Basic info
    "Rk":       None,   # dropped
    "Pk":       "pick",
    "Tm":       "team",
    "Player":   "player_name",
    "College":  "college",
    "Yrs":      "career_years",
    # Totals section
    "Totals_G":    "career_games",
    "Totals_MP":   "career_mp",
    "Totals_PTS":  "career_pts",
    "Totals_TRB":  "career_trb",
    "Totals_AST":  "career_ast",
    "Totals_FG%":  "career_fg_pct",
    "Totals_3P%":  "career_3p_pct",
    "Totals_FT%":  "career_ft_pct",
    # Per Game section
    "Per Game_MP":  "pg_mp",
    "Per Game_PTS": "pg_pts",
    "Per Game_TRB": "pg_trb",
    "Per Game_AST": "pg_ast",
    # Advanced
    "WS":      "win_shares",
    "WS/48":   "ws_per_48",
    "BPM":     "bpm",
    "VORP":    "vorp",
}

DROP_TOP = {"Rk"}


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    BBR draft pages use a two-level header.
    Top-level labels like 'Totals' and 'Per Game' prefix their sub-columns;
    columns without a meaningful top-level label keep only their bottom name.
    """
    if not isinstance(df.columns, pd.MultiIndex):
        return df

    new_cols = []
    for top, bot in df.columns:
        top = str(top).strip()
        bot = str(bot).strip()
        # BBR uses 'Unnamed: X_level_0' for columns with no top-level header
        if top.startswith("Unnamed") or top == "":
            new_cols.append(bot)
        else:
            new_cols.append(f"{top}_{bot}")
    df.columns = new_cols
    return df


def _parse_draft_page(driver: webdriver.Chrome, year: int) -> pd.DataFrame | None:
    """Navigate to the draft page for *year* and return a cleaned DataFrame."""
    url = f"https://www.basketball-reference.com/draft/NBA_{year}.html"
    driver.get(url)
    time.sleep(NAV_SLEEP)

    soup = BeautifulSoup(driver.page_source, "lxml")
    soup = uncomment_tables(soup)

    try:
        table = get_table(soup, TABLE_ID)
    except ValueError:
        print(f"  WARNING: table #{TABLE_ID} not found for {year} — skipping")
        return None

    df = pd.read_html(str(table))[0]
    df = _flatten_columns(df)

    # Drop rows that are repeated headers or empty picks ("Player" == "Player")
    if "Player" in df.columns:
        df = df[df["Player"].notna()]
        df = df[df["Player"].astype(str).str.strip() != "Player"]
        df = df[df["Player"].astype(str).str.strip() != ""]

    # Attach draft year before renaming so the column survives
    df["draft_year"] = year

    # Determine round from the "Rnd" column if present, else derive from pick order
    if "Rnd" in df.columns:
        df = df.rename(columns={"Rnd": "round"})
    elif "Round" in df.columns:
        df = df.rename(columns={"Round": "round"})

    # Apply RENAME map — only rename columns that exist
    rename_map = {k: v for k, v in RENAME.items() if k in df.columns and v is not None}
    drop_cols  = [k for k, v in RENAME.items() if k in df.columns and v is None]
    df = df.rename(columns=rename_map)
    df = df.drop(columns=drop_cols, errors="ignore")

    # Drop any remaining unlabelled rank-like columns
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")], errors="ignore")

    return df.reset_index(drop=True)


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
