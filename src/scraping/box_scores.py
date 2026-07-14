"""
Scraper: BBR box scores — per-player per-game stats for a date range.
Output:  dbt/seeds/box_scores.csv

Usage:
    # Scrape a specific date
    python box_scores.py --date 2026-04-30

    # Scrape a date range
    python box_scores.py --start 2026-04-01 --end 2026-04-30

    # Default: scrape yesterday (useful for daily cron)
    python box_scores.py

Scale note:
    One full regular season (~1,230 games) takes ~1–1.5 hours with a
    single browser session and 3-second page sleep. For multi-season
    historical data (40 years ≈ 49,200 games) direct PostgreSQL writes
    are required — see docs/box_score_architecture.md.

HTML structure:
    Index page:  /boxscores/index.fcgi?month=M&day=D&year=Y
        Game links match: /boxscores/YYYYMMDD0ABC.html

    Box score page: /boxscores/YYYYMMDD0ABC.html
        Table IDs (inside HTML comments):
            box-{TEAM3}-game-basic    — per-player box score (both teams)
        Columns: Player, MP, FG, FGA, FG%, 3P, 3PA, 3P%, FT, FTA, FT%,
                 ORB, DRB, TRB, AST, STL, BLK, TOV, PF, PTS, +/-
"""

import argparse
import io
import os
import re
import time
from datetime import date, timedelta, datetime

import pandas as pd
from bs4 import BeautifulSoup

from common.browser import build_driver
from common.parsing import uncomment_tables

OUTPUT = os.path.join(os.path.dirname(__file__), "../../dbt/seeds/box_scores.csv")
NAV_SLEEP = 3   # seconds between page navigations (single session)

# Columns with SQL-unsafe names that need renaming before saving
RENAME = {
    "FG%":  "fg_pct",
    "3P":   "three_p",
    "3PA":  "three_pa",
    "3P%":  "three_p_pct",
    "FT%":  "ft_pct",
    "+/-":  "plus_minus",
}

DROP = ["Rk"]


def _index_url(d: date) -> str:
    return (
        f"https://www.basketball-reference.com/boxscores/"
        f"index.fcgi?month={d.month}&day={d.day}&year={d.year}"
    )


def _game_urls_from_index(soup: BeautifulSoup) -> list[str]:
    """Return all box score hrefs found on a daily index page."""
    pattern = re.compile(r"^/boxscores/\d{8}0[A-Z]+\.html$")
    links = soup.find_all("a", href=pattern)
    return list(dict.fromkeys(a["href"] for a in links))  # dedup, preserve order


def _team_from_table_id(table_id: str) -> str:
    """Extract team abbreviation from 'box-BOS-game-basic' → 'BOS'."""
    parts = table_id.split("-")
    return parts[1] if len(parts) >= 2 else ""


def _parse_box_table(table, team: str, home_away: str, game_id: str, game_date: str) -> pd.DataFrame:
    df = pd.read_html(io.StringIO(str(table)))[0]

    # Drop multi-level header if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(-1)

    # Remove totals row and header repetitions
    df = df[df["Player"].notna()]
    df = df[df["Player"].str.strip() != "Player"]
    df = df[df["Player"].str.strip() != "Team Totals"]
    df = df[df["MP"].notna()]
    df = df[df["MP"].astype(str).str.strip() != "Did Not Play"]
    df = df[df["MP"].astype(str).str.strip() != "Did Not Dress"]
    df = df[df["MP"].astype(str).str.strip() != "Not With Team"]
    df = df[df["MP"].astype(str).str.strip() != "Inactive"]

    df = df.drop(columns=[c for c in DROP if c in df.columns], errors="ignore")
    df = df.rename(columns=RENAME)

    df["game_id"]   = game_id
    df["game_date"] = game_date
    df["team"]      = team
    df["home_away"] = home_away

    return df.reset_index(drop=True)


def _parse_game_page(driver, url: str) -> list[pd.DataFrame]:
    """Scrape both teams' basic box scores from a single game page."""
    driver.get(url)
    time.sleep(NAV_SLEEP)

    soup = BeautifulSoup(driver.page_source, "lxml")
    soup = uncomment_tables(soup)

    # game_id = last path component without .html, e.g. "202604300BOS"
    game_id   = url.split("/")[-1].replace(".html", "")
    game_date = f"{game_id[:4]}-{game_id[4:6]}-{game_id[6:8]}"

    # Find all basic box score tables for both teams
    tables = soup.find_all("table", id=re.compile(r"^box-[A-Z]+-game-basic$"))

    if not tables:
        print(f"    WARNING: no box score tables found in {url}")
        return []

    frames = []
    # BBR puts the away team first, home team second
    for i, table in enumerate(tables):
        team      = _team_from_table_id(table.get("id", ""))
        home_away = "home" if i == len(tables) - 1 else "away"
        df = _parse_box_table(table, team, home_away, game_id, game_date)
        if not df.empty:
            frames.append(df)

    return frames


def scrape_date_range(start: date, end: date) -> pd.DataFrame:
    all_frames = []
    driver = build_driver()

    try:
        current = start
        while current <= end:
            print(f"\n[{current}] Fetching game index...")
            driver.get(_index_url(current))
            time.sleep(NAV_SLEEP)

            soup = BeautifulSoup(driver.page_source, "lxml")
            game_paths = _game_urls_from_index(soup)

            if not game_paths:
                print(f"  No games found on {current}")
                current += timedelta(days=1)
                continue

            print(f"  Found {len(game_paths)} game(s)")
            for path in game_paths:
                url = f"https://www.basketball-reference.com{path}"
                print(f"  Scraping {url.split('/')[-1]} ...", end=" ", flush=True)
                frames = _parse_game_page(driver, url)
                if frames:
                    all_frames.extend(frames)
                    rows = sum(len(f) for f in frames)
                    print(f"{rows} player rows")
                else:
                    print("skipped")

            current += timedelta(days=1)
    finally:
        driver.quit()

    if not all_frames:
        return pd.DataFrame()

    return pd.concat(all_frames, ignore_index=True)


def _parse_args():
    parser = argparse.ArgumentParser(description="Scrape BBR box scores for a date range")
    parser.add_argument("--date",  help="Single date (YYYY-MM-DD)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end",   help="End date (YYYY-MM-DD)")
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d").date()
        start = end = d
    elif args.start and args.end:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end   = datetime.strptime(args.end,   "%Y-%m-%d").date()
    else:
        # Default: yesterday
        start = end = date.today() - timedelta(days=1)

    print(f"Scraping box scores: {start} → {end}")
    df = scrape_date_range(start, end)

    if df.empty:
        print("No data scraped.")
        return

    out = os.path.abspath(OUTPUT)

    if os.path.exists(out):
        existing = pd.read_csv(out)
        before = len(existing)

        # UPSERT: concatenate everything and keep the MOST RECENT record per (game_id, Player).
        # This ensures late BBR corrections overwrite old data, instead of the
        # previous behavior that silently discarded updates.
        combined = pd.concat([existing, df], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["game_id", "Player"],
            keep="last",   # "last" = new scrape wins; use "first" to preserve history
        )

        updated = len(combined) - before
        print(f"  UPSERT: {len(df)} new rows / {before} existing → {len(combined)} total")
        if updated > 0:
            print(f"  ({updated} rows inserted or updated)")
    else:
        combined = df

    combined.to_csv(out, index=False)
    print(f"Saved {len(combined)} total player-game rows → {out}")


if __name__ == "__main__":
    main()
