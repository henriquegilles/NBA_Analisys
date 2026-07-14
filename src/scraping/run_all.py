"""
Run all BBR scrapers in sequence and report results.

Usage (from project root):
    cd src/scraping
    uv run python run_all.py

Each scraper writes its CSV to dbt/seeds/ directly.
After this script completes, run the dbt pipeline:
    cd dbt
    uv run dbt seed
    uv run dbt run
    uv run dbt test
"""

import sys
import traceback

SCRAPERS = [
    # players must run first — player_gamelogs depends on bbr_id from players.csv
    ("players", "players.main"),
    ("stats", "stats.main"),
    ("advanced_stats", "advanced_stats.main"),
    ("teams", "teams.main"),
    ("contracts", "contracts.main"),
    # Game logs depend on players.csv existing with bbr_id column
    ("player_gamelogs", "player_gamelogs.main"),
    # Draft is intentionally last: single browser session, ~40 pages, ~2-3 min
    ("draft", "draft.main"),
]


def run():
    results = []
    for name, dotted in SCRAPERS:
        module_name, func_name = dotted.rsplit(".", 1)
        print(f"\n{'=' * 50}")
        print(f"Running {name} scraper...")
        print(f"{'=' * 50}")
        try:
            import importlib

            mod = importlib.import_module(module_name)
            getattr(mod, func_name)()
            results.append((name, "OK"))
        except Exception:
            traceback.print_exc()
            results.append((name, "FAILED"))

    print("\n\nSummary")
    print("-------")
    for name, status in results:
        mark = "✓" if status == "OK" else "✗"
        print(f"  {mark} {name}: {status}")

    failed = [n for n, s in results if s != "OK"]
    if failed:
        print(f"\n{len(failed)} scraper(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\nAll scrapers completed successfully.")


if __name__ == "__main__":
    run()
