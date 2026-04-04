"""
Scraper: BBR per-game full stats (players_stats.csv)
Extracts all statistical columns, renaming SQL-unsafe column names.
Output:   seeds/players_stats.csv
"""

import os
import pandas as pd
from bs4 import BeautifulSoup

from common.browser import fetch_page
from common.parsing import uncomment_tables, get_table

SEASON = os.getenv("BBR_SEASON", "2025")
URL = f"https://www.basketball-reference.com/leagues/NBA_{SEASON}_per_game.html"
OUTPUT = os.path.join(os.path.dirname(__file__), "../../seeds/players_stats.csv")

# Columns with special characters that are invalid SQL identifiers.
# Rename them before saving so dbt seed can load the CSV without errors.
RENAME = {
    "FG%": "fg_pct",
    "3P": "three_p",
    "3PA": "three_pa",
    "3P%": "three_p_pct",
    "2P": "two_p",
    "2PA": "two_pa",
    "2P%": "two_p_pct",
    "eFG%": "efg_pct",
    "FT%": "ft_pct",
}

DROP = ["Rk", "Awards"]


def scrape() -> pd.DataFrame:
    driver = fetch_page(URL)
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

    soup = uncomment_tables(soup)
    table = get_table(soup, "per_game_stats")

    df = pd.read_html(str(table))[0]
    df = df[df["Player"].notna()]
    df = df[df["Player"].str.strip() != "Player"]
    df = df[df["Player"].str.strip() != "League Average"]

    # Drop columns that cause parsing issues or are not needed
    df = df.drop(columns=[c for c in DROP if c in df.columns])

    # Rename SQL-unsafe column names
    df = df.rename(columns=RENAME)

    return df.reset_index(drop=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")


if __name__ == "__main__":
    main()
