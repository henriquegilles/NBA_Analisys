"""
Gera amostras pequenas e CONSISTENTES dos seeds para o CI.

O dado real fica gitignorado/regenerável; o CI usa estas amostras para rodar
`dbt seed → run → test` de ponta a ponta sem committar a base inteira.

Consistência (para não quebrar os testes de FK dos marts): escolhe um conjunto
fixo de jogadores (por bbr_id) presente em players.csv E player_gamelogs.csv, e
filtra todos os seeds de jogador por esse conjunto. Os seeds de time são pequenos
e vão inteiros. draft e college vão como fatia (head), suficientes para os marts.

Uso:
    source .venv/bin/activate
    python ci/make_sample_seeds.py
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "seeds"
OUT = ROOT / "ci" / "sample_seeds"
OUT.mkdir(parents=True, exist_ok=True)

N_PLAYERS = 25          # jogadores no recorte consistente
N_DRAFT = 200           # linhas do draft
N_COLLEGE = 200         # linhas de college


def write(df: pd.DataFrame, name: str):
    df.to_csv(OUT / name, index=False)
    print(f"  {name}: {len(df)} linhas")


def main():
    players = pd.read_csv(SRC / "players.csv")
    gamelogs = pd.read_csv(SRC / "player_gamelogs.csv")

    # Conjunto consistente: bbr_ids em ambos os seeds.
    common_ids = sorted(set(players["bbr_id"].dropna()) & set(gamelogs["bbr_id"].dropna()))
    pick_ids = common_ids[:N_PLAYERS]
    names = set(players.loc[players["bbr_id"].isin(pick_ids), "Player"].dropna())
    print(f"Jogadores no recorte: {len(pick_ids)} bbr_ids, {len(names)} nomes")

    # Seeds de jogador filtrados pelo recorte.
    write(players[players["bbr_id"].isin(pick_ids)], "players.csv")
    write(gamelogs[gamelogs["bbr_id"].isin(pick_ids)], "player_gamelogs.csv")

    for fname in ["players_stats.csv", "players_advanced_stats.csv"]:
        df = pd.read_csv(SRC / fname)
        write(df[df["Player"].isin(names)], fname)

    contracts = pd.read_csv(SRC / "contracts.csv")
    write(contracts[contracts["Player"].isin(names)], "contracts.csv")

    # box_scores é minúsculo — vai inteiro.
    write(pd.read_csv(SRC / "box_scores.csv"), "box_scores.csv")

    # Seeds de time: pequenos, vão inteiros (cobrem todas as abreviações de FK).
    write(pd.read_csv(SRC / "team.csv"), "team.csv")
    write(pd.read_csv(SRC / "team_info.csv"), "team_info.csv")

    # Seed manual de overrides de identidade (D-09): pequeno, vai inteiro.
    write(pd.read_csv(SRC / "college_nba_id_overrides.csv"),
          "college_nba_id_overrides.csv")

    # draft e college: fatia (head) basta para os marts do Domínio B.
    draft = pd.read_csv(SRC / "draft.csv").head(N_DRAFT)
    if "bbr_id" not in draft.columns:  # draft.csv antigo (sem slug) — coluna vazia
        draft["bbr_id"] = pd.NA
    write(draft, "draft.csv")
    write(pd.read_csv(SRC / "college_player_seasons.csv").head(N_COLLEGE),
          "college_player_seasons.csv")

    # nba_player_careers: pequeno (só os matches da ponte) → vai inteiro se existir.
    # Se ainda não foi raspado, escreve só o cabeçalho para o ref() resolver no CI
    # (as 6 cats novas ficam NULL via left join — pipeline roda igual).
    careers_path = SRC / "nba_player_careers.csv"
    careers_cols = ["bbr_id", "player_name", "career_games",
                    "pg_pts", "pg_trb", "pg_ast",
                    "pg_stl", "pg_blk", "pg_fg3", "pg_tov"]
    careers = pd.read_csv(careers_path) if careers_path.exists() \
        else pd.DataFrame(columns=careers_cols)
    write(careers, "nba_player_careers.csv")

    print(f"\nAmostras escritas em {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
