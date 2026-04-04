"""
Scraper: BBR team history summary (team.csv)
Output:   seeds/team.csv
"""

import os
import pandas as pd
from bs4 import BeautifulSoup

from common.browser import fetch_page
from common.parsing import uncomment_tables, get_table

URL = "https://www.basketball-reference.com/teams/"
OUTPUT = os.path.join(os.path.dirname(__file__), "../../seeds/team.csv")

RENAME = {
    "W/L%": "wl_pct",
}


def scrape() -> pd.DataFrame:
    driver = fetch_page(URL)
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

    soup = uncomment_tables(soup)
    table = get_table(soup, "teams_active")

    df = pd.read_html(str(table))[0]

    # BBR uses multi-level columns on this page; flatten them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(str(c) for c in col).strip() for col in df.columns]

    df = df.rename(columns=RENAME)
    df = df[df["Franchise"].notna()]
    df = df[df["Franchise"].str.strip() != "Franchise"]

    return df.reset_index(drop=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")


if __name__ == "__main__":
    main()
