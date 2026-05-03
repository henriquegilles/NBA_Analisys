"""
Scraper: BBR player contracts (contracts.csv)
Output:   seeds/contracts.csv

Note: contracts.csv is not yet consumed by the dbt pipeline.
It is scraped and stored for future use in salary analysis.
"""

import os
import pandas as pd
from bs4 import BeautifulSoup

from common.browser import fetch_page
from common.parsing import uncomment_tables, get_table

URL = "https://www.basketball-reference.com/contracts/players.html"
OUTPUT = os.path.join(os.path.dirname(__file__), "../../seeds/contracts.csv")


def scrape() -> pd.DataFrame:
    driver = fetch_page(URL)
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

    soup = uncomment_tables(soup)
    table = get_table(soup, "player-contracts")

    df = pd.read_html(str(table))[0]

    # Flatten multi-level headers (BBR uses season years as sub-headers)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(str(c) for c in col).strip("_") for col in df.columns]

    df = df[df.iloc[:, 0].notna()]
    df = df[df.iloc[:, 0].astype(str).str.strip() != "Player"]

    return df.reset_index(drop=True)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")


if __name__ == "__main__":
    main()
