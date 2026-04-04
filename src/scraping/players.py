"""
Scraper: BBR per-game player roster (players.csv)
Extracts: Player, Age, Team, Pos
Output:   seeds/players.csv
"""

import os
import pandas as pd
from bs4 import BeautifulSoup

from common.browser import fetch_page
from common.parsing import uncomment_tables, get_table

SEASON = os.getenv("BBR_SEASON", "2025")
URL = f"https://www.basketball-reference.com/leagues/NBA_{SEASON}_per_game.html"
OUTPUT = os.path.join(os.path.dirname(__file__), "../../seeds/players.csv")

COLUMNS = ["Player", "Age", "Team", "Pos"]


def scrape() -> pd.DataFrame:
    driver = fetch_page(URL)
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

    soup = uncomment_tables(soup)
    table = get_table(soup, "per_game_stats")

    df = pd.read_html(str(table))[0]
    df = df[df["Player"].notna()]
    df = df[df["Player"].str.strip() != "Player"]  # remove repeated headers
    df = df[df["Player"].str.strip() != "League Average"]

    return df[COLUMNS].reset_index(drop=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")


if __name__ == "__main__":
    main()
