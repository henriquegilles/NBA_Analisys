"""
Scraper: NBA player CAREER per-game stats (nba_player_careers.csv)

Closes the missing half of the fantasy Domain B outcome. The `draft` seed only
carries pts/trb/ast of career per-game; the 6-cat "Bandeja de 3" outcome also
needs stocks (stl+blk), 3PM and TOV. Those live on each player's BBR page, in the
**Career** row of the per-game table — this scraper pulls exactly that row.

Targets (who to scrape): NOT every drafted player (~2400 pages). We only need the
prospects the college→NBA bridge actually matches. So we recompute that match in
pandas here — latest college season per player ⋈ draft on (name, draft-year window
±1) — and scrape only those NBA slugs (~the 96 backbone outcomes). The slug comes
from the `bbr_id` column draft.py now captures from the draft-page hrefs.

Join key downstream = `bbr_id` (NBA slug): int_prospect__nba_bridge LEFT JOINs this
seed on the draft row's slug, so a missing career just leaves the new cats NULL.

Output:  dbt/seeds/nba_player_careers.csv  (grain: 1 row per NBA player)
URL:     basketball-reference.com/players/{slug[0]}/{slug}.html
Table:   per_game  → row whose first cell == "Career"

Run standalone (NOT part of run_all.py — depends on a fresh draft.csv w/ bbr_id):
    cd src/scraping
    uv run python draft.py                  # first: (re)scrape draft to get bbr_id slugs
    uv run python nba_careers.py            # scrape careers for the bridge-matched set
    uv run python nba_careers.py --max-pages 4   # smoke test
    uv run python nba_careers.py --all      # every drafted player (~2400 pages, slow)
"""

import argparse
import os
import re
import time

import pandas as pd
from bs4 import BeautifulSoup

from common.browser import build_driver
from common.parsing import uncomment_tables

SEEDS = os.path.join(os.path.dirname(__file__), "../../dbt/seeds")
DRAFT_CSV = os.path.join(SEEDS, "draft.csv")
COLLEGE_CSV = os.path.join(SEEDS, "college_player_seasons.csv")
OUTPUT = os.path.join(SEEDS, "nba_player_careers.csv")

# Seconds between page navigations (single reused session, like draft.py).
NAV_SLEEP = 3

# Candidate ids for the per-game table (BBR has renamed it over time).
PER_GAME_TABLE_IDS = ["per_game", "per_game_stats"]

# data-stat → output column. The Career-row cell for each stat (per-game averages
# + total games). data-stat names are already SQL-safe.
CAREER_STATS = {
    "g":          "career_games",
    "pts_per_g":  "pg_pts",
    "trb_per_g":  "pg_trb",
    "ast_per_g":  "pg_ast",
    "stl_per_g":  "pg_stl",
    "blk_per_g":  "pg_blk",
    "fg3_per_g":  "pg_fg3",
    "tov_per_g":  "pg_tov",
}

OUTPUT_COLS = ["bbr_id", "player_name"] + list(CAREER_STATS.values())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape NBA player career per-game stats")
    parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Cap on player pages to fetch (smoke test).",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Scrape every drafted player in draft.csv, not just bridge-matched.",
    )
    return parser.parse_args()


def _bridge_matched_slugs() -> list[str]:
    """
    Recompute the college→NBA bridge match in pandas and return the NBA slugs to
    scrape. Mirrors int_prospect__nba_bridge: latest college season per player
    joined to draft on normalized name + draft-year window (±1). A loose superset
    is fine — SQL stays the authority for the actual join; we only decide WHO to
    scrape, and over-scraping a few extras is harmless.
    """
    draft = pd.read_csv(DRAFT_CSV)
    if "bbr_id" not in draft.columns:
        raise SystemExit(
            "draft.csv has no 'bbr_id' column — re-run `python draft.py` first so "
            "the NBA player slugs are captured."
        )
    draft = draft.dropna(subset=["bbr_id", "player_name", "draft_year"]).copy()
    draft["_name"] = draft["player_name"].str.strip().str.lower()
    draft["draft_year"] = draft["draft_year"].astype(int)

    college = pd.read_csv(COLLEGE_CSV).dropna(subset=["player", "season"]).copy()
    # latest college season per prospect (season label sorts lexically by YYYY)
    college = college.sort_values("season").groupby("cbb_id", as_index=False).last()
    college["_name"] = college["player"].str.strip().str.lower()
    college["_end"] = college["season"].str[:4].astype(int) + 1

    m = college.merge(draft, on="_name")
    m = m[(m["draft_year"] >= m["_end"] - 1) & (m["draft_year"] <= m["_end"] + 1)]
    return sorted(set(m["bbr_id"].dropna()))


def _all_draft_slugs() -> list[str]:
    draft = pd.read_csv(DRAFT_CSV)
    if "bbr_id" not in draft.columns:
        raise SystemExit("draft.csv has no 'bbr_id' column — re-run `python draft.py` first.")
    return sorted(set(draft["bbr_id"].dropna()))


# The career-total row in the footer is labelled either "Career" or "N Yrs"
# (e.g. "1 Yr", "14 Yrs") depending on BBR's current template — match both.
CAREER_LABEL = re.compile(r"^(career|\d+\s+yrs?)$", re.I)


def _find_per_game_table(soup: BeautifulSoup):
    for tid in PER_GAME_TABLE_IDS:
        table = soup.find("table", {"id": tid})
        if table is not None:
            return table
    # last resort: regular-season per_game table (skip playoffs "_post").
    return soup.find(
        "table",
        id=lambda v: v and v.startswith("per_game") and not v.endswith("_post"),
    )


def _career_row(table):
    """Return the career-total <tr> from the table footer ('Career' or 'N Yrs')."""
    foot = table.find("tfoot")
    rows = foot.find_all("tr") if foot else []
    for tr in rows:
        first = tr.find(["th", "td"])
        if first and CAREER_LABEL.match(first.get_text(strip=True)):
            return tr
    return rows[0] if rows else None  # fallback: first footer row


def _scrape_one(driver, slug: str) -> dict | None:
    url = f"https://www.basketball-reference.com/players/{slug[0]}/{slug}.html"
    driver.get(url)
    time.sleep(NAV_SLEEP)
    soup = uncomment_tables(BeautifulSoup(driver.page_source, "lxml"))

    table = _find_per_game_table(soup)
    if table is None:
        print(f"  WARNING: no per_game table for {slug} — skipping")
        return None
    row = _career_row(table)
    if row is None:
        print(f"  WARNING: no Career row for {slug} — skipping")
        return None

    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else slug

    out = {"bbr_id": slug, "player_name": name}
    for stat, col in CAREER_STATS.items():
        cell = row.find(attrs={"data-stat": stat})
        out[col] = cell.get_text(strip=True) if cell else None
    return out


def scrape() -> pd.DataFrame:
    args = _parse_args()
    slugs = _all_draft_slugs() if args.all else _bridge_matched_slugs()
    if args.max_pages:
        slugs = slugs[: args.max_pages]

    scope = "all drafted" if args.all else "bridge-matched"
    print(f"Scraping {len(slugs)} NBA careers ({scope})")
    if not slugs:
        raise RuntimeError("No target slugs — is draft.csv populated with bbr_id?")

    driver = build_driver()
    rows = []
    try:
        for i, slug in enumerate(slugs, 1):
            print(f"  [{i}/{len(slugs)}] {slug} ...", end=" ", flush=True)
            try:
                row = _scrape_one(driver, slug)
            except Exception as exc:  # one bad page shouldn't kill the run
                print(f"ERROR: {exc}")
                continue
            if row:
                rows.append(row)
                print(f"{row['career_games']} G, {row['pg_pts']} pts")
    finally:
        driver.quit()

    if not rows:
        raise RuntimeError("No careers scraped — all pages failed.")

    return pd.DataFrame(rows).reindex(columns=OUTPUT_COLS)


def main():
    df = scrape()
    out = os.path.abspath(OUTPUT)
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} player careers → {out}")


if __name__ == "__main__":
    main()
