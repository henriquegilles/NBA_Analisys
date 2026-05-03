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

import argparse
import io
import os
import time
import re

import pandas as pd
from bs4 import BeautifulSoup

from common.browser import build_driver
from common.parsing import uncomment_tables, get_table

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape BBR player game logs")
    parser.add_argument(
        "--season",
        default=None,
        help="Season label (ex: 2025-26). Overrides BBR_SEASON env var.",
    )
    return parser.parse_args()

_args = _parse_args()

if _args.season:
    # Accept "YYYY-YY" format from Dagster and convert to end-year integer
    SEASON = str(int(_args.season.split("-")[0]) + 1)
else:
    SEASON = os.getenv("BBR_SEASON", "2026")

_season_label = f"{int(SEASON)-1}-{str(SEASON)[2:]}"

# players.csv is written to seeds/ relative to repo root
_script_dir = os.path.dirname(__file__)
PLAYERS_CSV = os.path.join(_script_dir, "../../seeds/players.csv")
OUTPUT      = os.path.join(_script_dir, "../../seeds/player_gamelogs.csv")

TABLE_ID  = "player_game_log_reg"
NAV_SLEEP = 3  # seconds between page navigations

# Columns with SQL-unsafe or duplicate names in the BBR game log table
RENAME = {
    "Date":  "game_date",
    "Team":  "team",
    "Opp":   "opponent",
    "Result":"game_result",
    "GS":    "games_started",
    "MP":    "minutes_played",
    "FG%":   "fg_pct",
    "3P":    "three_p",
    "3PA":   "three_pa",
    "3P%":   "three_p_pct",
    "FT%":   "ft_pct",
    "GmSc":  "game_score",
    "+/-":   "plus_minus",
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

    df = pd.read_html(io.StringIO(str(table)))[0]

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

    # Drop auxiliary counter columns (no analytical value)
    df = df.drop(columns=["Rk", "Gcar", "Gtm", "game_number"], errors="ignore")
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
    return df[["Player", "bbr_id"]].dropna().drop_duplicates(subset=["bbr_id"])


def _already_scraped_ids(out_path: str) -> set:
    """Return set of bbr_ids already written to the output CSV (for resume)."""
    if not os.path.exists(out_path):
        return set()
    try:
        existing = pd.read_csv(out_path, usecols=["bbr_id"])
        return set(existing["bbr_id"].dropna().unique())
    except Exception:
        return set()


def _append_to_csv(df: pd.DataFrame, out_path: str) -> None:
    """Append a player's rows to the output CSV, writing header only on first write."""
    write_header = not os.path.exists(out_path)
    df.to_csv(out_path, mode="a", index=False, header=write_header)


def scrape(out_path: str) -> None:
    players = _load_players()
    done_ids = _already_scraped_ids(out_path)

    pending = players[~players["bbr_id"].isin(done_ids)]
    total = len(players)
    skipped = len(done_ids)

    if skipped:
        print(f"Resuming: {skipped} already done, {len(pending)} remaining ({total} total).")
    else:
        print(f"Scraping game logs for {total} players ({_season_label})...")

    failed = []
    driver = build_driver()
    driver_uses = 0

    try:
        for i, row in enumerate(pending.itertuples(), 1):
            print(
                f"  [{i + skipped}/{total}] {row.Player} ({row.bbr_id}) ...",
                end=" ", flush=True,
            )
            try:
                df = _parse_gamelog(driver, row.bbr_id, row.Player)
                driver_uses += 1
            except Exception:
                # Tab crashed or connection lost — restart the driver and retry once
                print("driver crash — restarting...", end=" ", flush=True)
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = build_driver()
                driver_uses = 0
                try:
                    df = _parse_gamelog(driver, row.bbr_id, row.Player)
                    driver_uses += 1
                except Exception:
                    df = None

            if df is not None and not df.empty:
                _append_to_csv(df, out_path)
                print(f"{len(df)} games")
            else:
                failed.append(row.Player)
                print("no data")

            # Restart Chrome every 150 players to avoid memory buildup
            if driver_uses >= 150:
                print("  [restart Chrome session]")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = build_driver()
                driver_uses = 0

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    if failed:
        print(f"\nNo data ({len(failed)} players): {', '.join(failed[:10])}"
              + ("..." if len(failed) > 10 else ""))


def main():
    out = os.path.abspath(OUTPUT)
    scrape(out)
    if os.path.exists(out):
        result = pd.read_csv(out)
        total_games = len(result)
        players = result["player_name"].nunique()
        print(f"\nSaved {total_games} player-game rows ({players} players) → {out}")


if __name__ == "__main__":
    main()
