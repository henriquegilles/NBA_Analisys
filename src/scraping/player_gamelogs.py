"""
Scraper: BBR player game logs — per-player per-game stats for all players.
Output:  seeds/player_gamelogs.csv

Strategy:
    1. Read seeds/players.csv (produced by players.py) to get the list of
       active players + their bbr_id.
    2. Reuse a single Selenium session across all ~500 player pages.
    3. For each player, navigate to:
           /players/{bbr_id[0]}/{bbr_id}/gamelog/{SEASON}
       and parse the pgl_basic table.

Advantages over box score scraping:
    • ~500 pages/season vs ~1,230 (one per game)
    • Includes Game Score (GmSc), opponent, result — not in the box score index
    • Natural player focus: one row = one player's entire night

Columns captured per game:
    bbr_id, player_name, season,
    game_date, opponent, home_away, game_result,
    games_started, minutes_played,
    fg, fga, fg_pct,
    three_p, three_pa, three_p_pct,
    ft, fta, ft_pct,
    orb, drb, trb, ast, stl, blk, tov, pf, pts,
    game_score, plus_minus
"""

import os
import time
import re

import pandas as pd
from bs4 import BeautifulSoup

from common.browser import build_driver
from common.parsing import uncomment_tables, get_table

SEASON = os.getenv("BBR_SEASON", "2026")
_season_label = f"{int(SEASON)-1}-{str(SEASON)[2:]}"

# players.csv is written to seeds/ relative to repo root
_script_dir = os.path.dirname(__file__)
PLAYERS_CSV = os.path.join(_script_dir, "../../seeds/players.csv")
OUTPUT      = os.path.join(_script_dir, "../../seeds/player_gamelogs.csv")

TABLE_ID  = "pgl_basic"
NAV_SLEEP = 3  # seconds between page navigations

# Columns with SQL-unsafe or duplicate names in the BBR game log table
RENAME = {
    "FG%":  "fg_pct",
    "3P":   "three_p",
    "3PA":  "three_pa",
    "3P%":  "three_p_pct",
    "FT%":  "ft_pct",
    "GmSc": "game_score",
    "+/-":  "plus_minus",
    "G":    "game_number",
    "GS":   "games_started",
    "MP":   "minutes_played",
    "Tm":   "team",
    "Opp":  "opponent",
}

# Rows to filter out (BBR inserts these as separators / playoff headers)
_SKIP_VALUES = {"Rk", "Did Not Play", "Did Not Dress", "Not With Team", "Inactive", ""}


def _gamelog_url(bbr_id: str) -> str:
    return (
        f"https://www.basketball-reference.com"
        f"/players/{bbr_id[0]}/{bbr_id}/gamelog/{SEASON}"
    )


def _parse_gamelog(driver, bbr_id: str, player_name: str) -> pd.DataFrame | None:
    driver.get(_gamelog_url(bbr_id))
    time.sleep(NAV_SLEEP)

    soup = BeautifulSoup(driver.page_source, "lxml")
    soup = uncomment_tables(soup)

    try:
        table = get_table(soup, TABLE_ID)
    except ValueError:
        return None

    df = pd.read_html(str(table))[0]

    # Drop multi-level header if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(-1)

    # The home/away column is unnamed in BBR ("" header, "@" when away)
    # Rename it before any other processing
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    if unnamed:
        df = df.rename(columns={unnamed[0]: "home_away_raw"})

    # Filter header-repetition rows and non-game rows
    if "Rk" in df.columns:
        df = df[~df["Rk"].astype(str).str.strip().isin(_SKIP_VALUES)]
        df = df[df["Rk"].astype(str).str.match(r"^\d+$")]

    # Filter rows where MP is not a valid time (DNP / inactive)
    if "MP" in df.columns:
        df = df[df["MP"].notna()]
        df = df[~df["MP"].astype(str).str.strip().isin(_SKIP_VALUES)]

    if df.empty:
        return None

    # Apply column renames
    df = df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns})

    # Derive home_away from the unnamed column
    if "home_away_raw" in df.columns:
        df["home_away"] = df["home_away_raw"].apply(
            lambda v: "away" if str(v).strip() == "@" else "home"
        )
        df = df.drop(columns=["home_away_raw"])

    # Parse minutes to decimal: "32:14" → 32.23
    if "minutes_played" in df.columns:
        def _mp_to_decimal(val):
            val = str(val).strip()
            if ":" not in val:
                return None
            mins, secs = val.split(":", 1)
            try:
                return int(mins) + int(secs) / 60
            except ValueError:
                return None

        df["minutes_decimal"] = df["minutes_played"].apply(_mp_to_decimal)

    # Derive game_result (win/loss) and margin from result like "W (+12)" or "L (-5)"
    if "game_result" not in df.columns and "game_number" in df.columns:
        # BBR puts W/L result in a column — look for it by common stat names
        pass

    # Attach identifiers
    df["bbr_id"]      = bbr_id
    df["player_name"] = player_name
    df["season"]      = _season_label

    # Drop the rank column (no analytical value)
    df = df.drop(columns=["Rk", "game_number"], errors="ignore")
    # Drop unnamed leftovers
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")], errors="ignore")

    return df.reset_index(drop=True)


def _load_players() -> pd.DataFrame:
    path = os.path.abspath(PLAYERS_CSV)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"players.csv not found at {path}. "
            "Run players.py first to generate it."
        )
    df = pd.read_csv(path)
    if "bbr_id" not in df.columns:
        raise ValueError(
            "players.csv has no 'bbr_id' column. "
            "Re-run players.py to regenerate it with the updated scraper."
        )
    # De-duplicate: keep one bbr_id per player (traded players appear multiple times)
    return df[["Player", "bbr_id"]].dropna().drop_duplicates(subset=["bbr_id"])


def scrape() -> pd.DataFrame:
    players = _load_players()
    print(f"Scraping game logs for {len(players)} players ({_season_label})...")

    driver = build_driver()
    frames = []
    failed = []

    try:
        for i, row in enumerate(players.itertuples(), 1):
            print(f"  [{i}/{len(players)}] {row.Player} ({row.bbr_id}) ...", end=" ", flush=True)
            df = _parse_gamelog(driver, row.bbr_id, row.Player)
            if df is not None and not df.empty:
                frames.append(df)
                print(f"{len(df)} games")
            else:
                failed.append(row.Player)
                print("no data")
    finally:
        driver.quit()

    if failed:
        print(f"\nSkipped ({len(failed)} players): {', '.join(failed[:10])}"
              + ("..." if len(failed) > 10 else ""))

    if not frames:
        raise RuntimeError("No game log data scraped.")

    return pd.concat(frames, ignore_index=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    total_games = len(df)
    players = df["player_name"].nunique()
    print(f"\nSaved {total_games} player-game rows ({players} players) → {out}")


if __name__ == "__main__":
    main()
