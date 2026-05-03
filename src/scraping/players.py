"""
Scraper: BBR per-game player roster (players.csv)
Extracts: Player, Age, Team, Pos, season, bbr_id

bbr_id comes from the data-append-csv attribute on each player cell
(e.g. "jamesle01") and is the key used to construct game log URLs:
    /players/{bbr_id[0]}/{bbr_id}/gamelog/{SEASON}

Output:   seeds/players.csv
"""

import io
import os
import pandas as pd
from bs4 import BeautifulSoup

from common.browser import fetch_page
from common.parsing import uncomment_tables, get_table

SEASON = os.getenv("BBR_SEASON", "2026")
_season_label = f"{int(SEASON)-1}-{str(SEASON)[2:]}"
URL = f"https://www.basketball-reference.com/leagues/NBA_{SEASON}_per_game.html"
OUTPUT = os.path.join(os.path.dirname(__file__), "../../seeds/players.csv")

COLUMNS = ["Player", "Age", "Team", "Pos"]


def _extract_bbr_ids(table) -> dict[str, str]:
    """Return {player_name: bbr_id} from data-append-csv attributes in the table."""
    mapping = {}
    for td in table.find_all("td", {"data-stat": "name_display"}):
        bbr_id = td.get("data-append-csv")
        name = td.get_text(strip=True)
        if bbr_id and name:
            mapping[name] = bbr_id
    return mapping


def scrape() -> pd.DataFrame:
    driver = fetch_page(URL)
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

    soup = uncomment_tables(soup)
    table = get_table(soup, "per_game_stats")

    bbr_ids = _extract_bbr_ids(table)

    df = pd.read_html(io.StringIO(str(table)))[0]
    df = df[df["Player"].notna()]
    df = df[df["Player"].str.strip() != "Player"]
    df = df[df["Player"].str.strip() != "League Average"]

    df = df[COLUMNS].copy()
    df["season"] = _season_label
    df["bbr_id"] = df["Player"].map(bbr_ids)

    return df.reset_index(drop=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")


if __name__ == "__main__":
    main()
