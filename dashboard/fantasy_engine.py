"""
Motor de métricas fantasy (Bandeja de 3) — versão reproduzível dos scripts pandas
que na sessão de decisão viviam ad-hoc em /tmp. Lê os seeds direto (não precisa do DB),
o que torna o protótipo portátil.

Responsabilidades:
  - carregar seeds (rosters da liga, stats NBA, gamelogs, draft class, landing spots)
  - z-score por categoria sobre pool de rotação (7-cat, TOV invertido)
  - VA punt-TOV = z_total - z_tov (métrica central)
  - per-36, floor/ceiling, consistência (gamelogs)
  - pool de FA, força de liga por categoria, cap, board de draft ajustado por oportunidade

Uso:
    from fantasy_engine import Engine
    eng = Engine()               # carrega tudo dos seeds
    eng.my_roster()              # DataFrame do meu time (Lobos)
    eng.fa_targets()             # alvos de FA ranqueados
    eng.draft_board()            # board de draft por oportunidade
    eng.league_strength()        # 24 times x categoria
    eng.team_cap()               # cap por franquia
"""
from __future__ import annotations
import os
import re
import unicodedata as ud

import numpy as np
import pandas as pd

SEEDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seeds")
MY_FRANCHISE = "Lobos Comunistas"
CAP = 190.0
CATS = ["PTS", "REB", "AST", "STOCKS", "3PM", "TOV"]


def norm(s: str) -> str:
    """Normaliza nome p/ join. Igual à macro dbt norm_name: sem acento, minúsculo,
    remove TODO não-alfanumérico (espaços/pontuação) — resolve acento (Dončić) E
    alinha com as chaves dos seeds (dariusacuffjr)."""
    s = ud.normalize("NFKD", str(s))
    s = "".join(c for c in s if not ud.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


class Engine:
    def __init__(self, seeds_dir: str = SEEDS):
        self.seeds = seeds_dir
        self._load()
        self._build_value()

    # ---------- carga ----------
    def _csv(self, name):
        return pd.read_csv(os.path.join(self.seeds, name))

    def _load(self):
        self.stats = self._csv("players_stats.csv")          # per-game 2025-26
        self.rosters = self._csv("fantasy_rosters.csv")
        self.draft = self._csv("fantasy_draft_class.csv")
        try:
            self.landing = self._csv("nba_landing_spots.csv")
        except FileNotFoundError:
            self.landing = pd.DataFrame(columns=["prospect_key", "nba_team_final", "opportunity_mult"])
        self.stats["key"] = self.stats["Player"].map(norm)
        # dedup: jogadores trocados têm >1 linha (TOT + times) -> fan-out no merge/cap.
        # Mantém a de mais jogos por jogador (1 valoração por pessoa).
        self.stats = (self.stats.sort_values("G", key=lambda s: s.map(_f), ascending=False)
                      .drop_duplicates("key", keep="first").reset_index(drop=True))
        self.rosters["key"] = self.rosters["nome_jogador"].map(norm)
        self.rosters = self.rosters.drop_duplicates(["nome_franquia", "key"], keep="first")

    # ---------- valoração 7-cat ----------
    def _cat_vector(self, df):
        return pd.DataFrame({
            "PTS": df["PTS"].map(_f), "REB": df["TRB"].map(_f), "AST": df["AST"].map(_f),
            "STOCKS": df["STL"].map(_f) + df["BLK"].map(_f),
            "3PM": df["three_p"].map(_f), "TOV": -df["TOV"].map(_f),
        })

    def _build_value(self):
        s = self.stats
        pool = s[(s["G"].map(_f) >= 25) & (s["MP"].map(_f) >= 18)]
        cv_pool = self._cat_vector(pool)
        mean, std = cv_pool.mean(), cv_pool.std(ddof=0).replace(0, 1)
        cv = self._cat_vector(s)
        z = (cv - mean) / std
        z.columns = [f"z_{c}" for c in CATS]
        val = s[["Player", "key", "Pos", "Age", "MP", "G", "three_pa", "three_p_pct", "ft_pct"]].copy()
        val = pd.concat([val, z], axis=1)
        val["z_total"] = z.sum(axis=1)
        val["VA"] = val["z_total"] - val["z_TOV"]          # punt-TOV
        # fit ponderado p/ Lobos (AST+3PM 1.5x)
        val["fit"] = z["z_PTS"] + z["z_REB"] + z["z_STOCKS"] + 1.5 * z["z_AST"] + 1.5 * z["z_3PM"]
        self.val = val.set_index("key")

    # ---------- helpers de roster ----------
    def _roster_with_value(self, franchise=None):
        r = self.rosters if franchise is None else self.rosters[self.rosters["nome_franquia"] == franchise]
        j = r.merge(self.val, left_on="key", right_index=True, how="left", suffixes=("", "_v"))
        j["salary_y1_m"] = j["salario_ano1"].map(_f).fillna(0) / 1e6
        return j

    # ---------- superfícies públicas ----------
    def my_roster(self):
        j = self._roster_with_value(MY_FRANCHISE)
        cols = ["nome_jogador", "posicao_1", "Age", "salary_y1_m", "VA",
                "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_TOV"]
        return (j[cols].rename(columns={"nome_jogador": "Jogador", "posicao_1": "Pos"})
                .sort_values("VA", ascending=False))

    def fa_targets(self, top=30):
        paid = set(self.rosters[self.rosters["salario_ano1"].map(_f).fillna(0) > 0]["key"])
        fa_bound = self.rosters[self.rosters["salario_ano1"].map(_f).fillna(0) == 0][["key", "nome_franquia"]]
        holder = dict(zip(fa_bound["key"], fa_bound["nome_franquia"]))
        s = self.stats
        pool = s[(s["G"].map(_f) >= 25) & (s["MP"].map(_f) >= 18)]["key"]
        avail = [k for k in pool if k not in paid]
        v = self.val.loc[[k for k in avail if k in self.val.index]].copy()
        v["held_by"] = [holder.get(k, "(livre)") for k in v.index]
        cols = ["Player", "Pos", "Age", "VA", "fit", "z_AST", "z_3PM", "z_STOCKS", "held_by"]
        return v[cols].rename(columns={"Player": "Jogador"}).sort_values("fit", ascending=False).head(top)

    def draft_board(self, top=25):
        d = self.draft.copy()
        d["key"] = d["nome"].map(norm)
        land = self.landing.set_index("prospect_key")["opportunity_mult"].to_dict() if len(self.landing) else {}
        team = self.landing.set_index("prospect_key")["nba_team_final"].to_dict() if len(self.landing) else {}
        # projeção viria do fct_prospect_scouting (DB). Sem DB, usa proxy do college se houver.
        d["opp_mult"] = d["key"].map(land).fillna(1.0)
        d["nba_team"] = d["key"].map(team).fillna("?")
        cols = ["nome", "posicao", "posicao_americana", "nba_team", "opp_mult"]
        return (d[cols].rename(columns={"nome": "Prospecto", "posicao": "Pos"})
                .sort_values("opp_mult", ascending=False).head(top))

    def league_strength(self):
        rows = []
        for fr, g in self._roster_with_value().groupby("nome_franquia"):
            top = g.dropna(subset=["VA"]).nlargest(10, "VA")
            rows.append({"Franquia": fr, **{c: round(top[f"z_{c}"].sum(), 1) for c in CATS},
                         "Total_VA": round(top["VA"].sum(), 1)})
        df = pd.DataFrame(rows).sort_values("Total_VA", ascending=False).reset_index(drop=True)
        df.insert(0, "Rank", df.index + 1)
        return df

    def team_cap(self):
        r = self._roster_with_value()
        agg = r.groupby("nome_franquia")["salary_y1_m"].sum().round(1)
        df = agg.reset_index().rename(columns={"nome_franquia": "Franquia", "salary_y1_m": "Folha_M"})
        df["Espaço_M"] = (CAP - df["Folha_M"]).round(1)
        return df.sort_values("Espaço_M", ascending=False).reset_index(drop=True)
