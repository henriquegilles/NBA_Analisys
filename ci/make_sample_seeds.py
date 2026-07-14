"""
Generate small, CONSISTENT samples of the seeds for CI.

The real data is gitignored/regenerable; CI uses these samples to run
`dbt seed → run → test` end to end without committing the full dataset.

Consistency (so the marts' FK tests don't break): pick a fixed set of players
(by bbr_id) present in BOTH players.csv and player_gamelogs.csv, and filter
every player seed by that set. Team seeds are small and go in whole. draft and
college go in as a slice (head), enough for the marts.

Usage:
    uv run python ci/make_sample_seeds.py
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dbt" / "seeds"
OUT = ROOT / "ci" / "sample_seeds"
OUT.mkdir(parents=True, exist_ok=True)

N_PLAYERS = 25          # players in the consistent subset
N_DRAFT = 200           # draft rows
N_COLLEGE = 200         # college rows


def write(df: pd.DataFrame, name: str):
    df.to_csv(OUT / name, index=False)
    print(f"  {name}: {len(df)} rows")


def main():
    players = pd.read_csv(SRC / "players.csv")
    gamelogs = pd.read_csv(SRC / "player_gamelogs.csv")

    # Consistent set: bbr_ids present in both seeds.
    common_ids = sorted(set(players["bbr_id"].dropna()) & set(gamelogs["bbr_id"].dropna()))
    pick_ids = common_ids[:N_PLAYERS]
    names = set(players.loc[players["bbr_id"].isin(pick_ids), "Player"].dropna())
    print(f"Players in the subset: {len(pick_ids)} bbr_ids, {len(names)} names")

    # Player seeds filtered by the subset.
    write(players[players["bbr_id"].isin(pick_ids)], "players.csv")
    write(gamelogs[gamelogs["bbr_id"].isin(pick_ids)], "player_gamelogs.csv")

    for fname in ["players_stats.csv", "players_advanced_stats.csv"]:
        df = pd.read_csv(SRC / fname)
        write(df[df["Player"].isin(names)], fname)

    contracts = pd.read_csv(SRC / "contracts.csv")
    write(contracts[contracts["Player"].isin(names)], "contracts.csv")

    # box_scores is tiny — goes in whole.
    write(pd.read_csv(SRC / "box_scores.csv"), "box_scores.csv")

    # Team seeds: small, go in whole (cover every FK abbreviation).
    write(pd.read_csv(SRC / "team.csv"), "team.csv")
    write(pd.read_csv(SRC / "team_info.csv"), "team_info.csv")

    # Manual identity-override seed (D-09): small, goes in whole.
    write(pd.read_csv(SRC / "college_nba_id_overrides.csv"),
          "college_nba_id_overrides.csv")

    # draft and college: a slice (head) is enough for the Domain B marts.
    draft = pd.read_csv(SRC / "draft.csv").head(N_DRAFT)
    if "bbr_id" not in draft.columns:  # old draft.csv (no slug) — empty column
        draft["bbr_id"] = pd.NA
    write(draft, "draft.csv")
    write(pd.read_csv(SRC / "college_player_seasons.csv").head(N_COLLEGE),
          "college_player_seasons.csv")

    # nba_player_careers: small (bridge matches only) → goes in whole if it exists.
    # If not scraped yet, write just the header so ref() resolves in CI
    # (the 6 new cats stay NULL via left join — the pipeline runs the same).
    careers_path = SRC / "nba_player_careers.csv"
    careers_cols = ["bbr_id", "player_name", "career_games",
                    "pg_pts", "pg_trb", "pg_ast",
                    "pg_stl", "pg_blk", "pg_fg3", "pg_tov"]
    careers = pd.read_csv(careers_path) if careers_path.exists() \
        else pd.DataFrame(columns=careers_cols)
    write(careers, "nba_player_careers.csv")

    # Fantasy seeds from the scraper (gitignored) referenced by stg_fantasy__*:
    # without a sample, `ref()` doesn't resolve and CI breaks at parse time.
    # They're small → go in whole, with `nome_usuario` anonymized (third-party
    # league data).
    for fname in ["fantasy_rosters.csv", "fantasy_franchises.csv",
                  "fantasy_standings.csv", "fantasy_draft_class.csv"]:
        if not (SRC / fname).exists():   # machine without an FGM scrape: keep the existing sample
            print(f"  {fname}: seed missing — existing sample kept")
            continue
        df = pd.read_csv(SRC / fname)
        if "nome_usuario" in df.columns and "codigo_franquia" in df.columns:
            df["nome_usuario"] = "user_" + df["codigo_franquia"].astype(str)
        write(df, fname)

    print(f"\nSamples written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
