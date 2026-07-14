"""
Fantasy metrics engine (Bandeja de 3) — reproducible version of the pandas
scripts that lived ad-hoc in /tmp during the decision session. Reads the seeds
directly (no DB needed), which keeps the prototype portable.

Responsibilities:
  - load seeds (league rosters, NBA stats, gamelogs, draft class, landing spots)
  - per-category z-score over the rotation pool (7-cat, TOV inverted)
  - punt-TOV VA = z_total - z_tov (the central metric)
  - per-36, floor/ceiling, consistency (gamelogs)
  - FA pool, league strength by category, cap, opportunity-adjusted draft board

Usage:
    from fantasy_engine import Engine
    eng = Engine()               # loads everything from the seeds
    eng.my_roster()              # DataFrame of my team (Lobos)
    eng.fa_targets()             # ranked FA targets
    eng.draft_board()            # opportunity-adjusted draft board
    eng.league_strength()        # 24 teams x category
    eng.team_cap()               # cap per franchise
"""
from __future__ import annotations
import os
import re
import unicodedata as ud

import numpy as np
import pandas as pd

SEEDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dbt", "seeds")
MY_FRANCHISE = "Lobos Comunistas"
CAP = 190.0
# The league's 7 REAL categories (win 4+ of 7 to take the matchup; TOV is our punt).
# PM (+/-) comes from the GAMELOGS — BBR's per-game table (players_stats) has no
# +/-, which is why the engine played with 6 cats until Round 6 (fixed: runbook #34).
CATS = ["PTS", "REB", "AST", "STOCKS", "3PM", "PM", "TOV"]
WIN_CATS = 4          # matchup: whoever wins 4+ of the 7 takes it (doc 06 §3)


def norm(s: str) -> str:
    """Normalizes a name for joins. Same as the dbt norm_name macro: strip accents,
    lowercase, remove EVERY non-alphanumeric char (spaces/punctuation) — handles
    accents (Dončić) AND matches the seed keys (dariusacuffjr)."""
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

    # ---------- loading ----------
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
        # dedup: traded players have >1 row (TOT + teams) -> fan-out in merge/cap.
        # Keep the row with the most games per player (1 valuation per person).
        self.stats = (self.stats.sort_values("G", key=lambda s: s.map(_f), ascending=False)
                      .drop_duplicates("key", keep="first").reset_index(drop=True))
        self._merge_plus_minus()
        self.rosters["key"] = self.rosters["nome_jogador"].map(norm)
        self.rosters = self.rosters.drop_duplicates(["nome_franquia", "key"], keep="first")
        self._apply_trade_overrides()
        self._apply_nba_context_overrides()
        self._load_banned()
        self._load_restricted()

    def _merge_plus_minus(self):
        """Per-game +/- from the GAMELOGS (BBR's per-game table has no +/-).
        Average plus_minus per game for the player (across every team of the
        season), tolerant coercion — the field arrives as a string ('+5'/'-3')
        and may contain repeated-header junk. Becomes the PM_pg column in
        self.stats."""
        try:
            gl = pd.read_csv(os.path.join(self.seeds, "player_gamelogs.csv"),
                             usecols=["player_name", "plus_minus", "team",
                                      "game_date", "game_result"], low_memory=False)
        except (FileNotFoundError, ValueError):
            self.stats["PM_pg"] = np.nan
            self.team_margin = {}
            return
        gl["pm"] = gl["plus_minus"].map(_f)
        gl["key"] = gl["player_name"].map(norm)
        pm = gl.groupby("key")["pm"].mean()
        self.stats["PM_pg"] = self.stats["key"].map(pm)
        # average TEAM margin per game ("W, 128-110" → +18), used to adjust the
        # PM of players who SWITCHED teams (see _apply_nba_context_overrides /
        # doc 09 §17.3)
        tg = gl.dropna(subset=["game_result"]).drop_duplicates(["team", "game_date"]).copy()
        sc = tg["game_result"].str.extract(r"(\d+)-(\d+)")
        margin = sc[0].map(_f) - sc[1].map(_f)
        self.team_margin = margin.groupby(tg["team"].values).mean().to_dict()
        # ORIGIN-team margin per PLAYER (average of the teams he actually played
        # for): resolves the seed's 'nba_team_old=2TM' (Vučević), which doesn't
        # exist in team_margin and would silently zero out the adjustment
        gl["_tmargin"] = gl["team"].map(self.team_margin)
        self.player_old_margin = gl.groupby("key")["_tmargin"].mean().to_dict()

    # known regimes of the context seed; a typo ('Injury') fails LOUDLY at load
    # time, not silently in the projection (the regime changes role_mult semantics)
    CONTEXT_CHANGE_TYPES = {"trade", "fa-signing", "waived", "injury", "re-sign"}
    CONTEXT_STATS_SEASON = "2025-26"   # the seed corrects THIS snapshot; once the
    # 2026-27 scrape is born with the right teams, the override stops matching on its own

    def _apply_nba_context_overrides(self):
        """Applies the July/2026 NBA context on top of the 2025-26 stats (which
        carry last season's team). Versioned seed `nba_context_overrides.csv`
        (player_name, nba_team_new, change_type, role_2026_27, role_mult, source):
        fixes the affected player's `Team` (minutes occupancy, context) and stores
        the 2026-27 role + multiplier for the predicts."""
        try:
            ov = self._csv("nba_context_overrides.csv")
        except FileNotFoundError:
            self.context = pd.DataFrame(
                columns=["key", "nba_team_new", "change_type",
                         "role_2026_27", "role_mult", "source"])
            return
        ov = ov[ov["player_name"].notna()].copy()
        bad = set(ov["change_type"].dropna()) - self.CONTEXT_CHANGE_TYPES
        if bad:
            raise ValueError(f"nba_context_overrides.csv: unknown change_type "
                             f"{bad} — valid regimes: {self.CONTEXT_CHANGE_TYPES}")
        ov["key"] = ov["player_name"].map(norm)
        # player with 2 rows (traded AND later injured): the most RECENT one wins
        ov = (ov.sort_values("date_confirmed")
                .drop_duplicates("key", keep="last"))
        team_map = dict(zip(ov["key"], ov["nba_team_new"]))
        known = set(self.stats["Team"].dropna()) | {"FA"}
        unknown = set(team_map.values()) - known
        if unknown:
            raise ValueError(f"nba_context_overrides.csv: team(s) outside the BBR "
                             f"standard: {unknown} (typo? use players_stats codes)")
        mask = (self.stats["key"].isin(team_map)
                & (self.stats.get("season", self.CONTEXT_STATS_SEASON)
                   == self.CONTEXT_STATS_SEASON))
        # +/- adjustment for a TEAM CHANGE (Phase 4 Improvement A, doc 09 §17.3):
        # PM_pg carries the old team — whoever left a bad team is punished in the
        # wrong category (Claxton/BKN). Shifts HALF the delta of average margin
        # between teams (shrinkage 0.5 = heuristic; the player's role changes too).
        tm = getattr(self, "team_margin", {})
        pom = getattr(self, "player_old_margin", {})
        if tm:
            # origin = margin of the teams the player PLAYED for (covers '2TM');
            # destination without a margin (waived → 'FA') = no adjustment, old PM stays
            adj = self.stats.loc[mask, "key"].map(
                lambda k: 0.5 * (tm.get(team_map.get(k), np.nan)
                                 - pom.get(k, np.nan)))
            self.stats.loc[mask, "PM_pg"] = (
                self.stats.loc[mask, "PM_pg"] + adj.fillna(0.0))
        self.stats.loc[mask, "Team"] = self.stats.loc[mask, "key"].map(team_map)
        self.context = ov.set_index("key", drop=False)

    def _load_banned(self):
        """Players BANNED from the league (cannot be rostered/targeted). Versioned
        seed `fantasy_banned_players.csv`. Becomes a set of normalized keys used to
        filter the FA pool and any target list. Empty if the seed doesn't exist."""
        try:
            b = self._csv("fantasy_banned_players.csv")
            self.banned = set(b["player_name"].dropna().map(norm))
        except FileNotFoundError:
            self.banned = set()

    def _load_restricted(self):
        """Players RESTRICTED in FA (each franchise protects 1 expiring $0 — the
        holder retains/matches, so they are not targets). Versioned seed
        `fantasy_restricted_players.csv`. Unlike banned players, they still count
        toward league strength (they remain rostered); they only leave the target
        lists. Empty if the seed doesn't exist."""
        try:
            r = self._csv("fantasy_restricted_players.csv")
            self.restricted = set(r["player_name"].dropna().map(norm))
        except FileNotFoundError:
            self.restricted = set()

    def _apply_trade_overrides(self):
        """Applies ALREADY-CLOSED trades on top of the scrape snapshot (which may be
        pre-trade). Versioned seed `fantasy_trade_overrides.csv` (player_name,
        to_franchise): reassigns the player (with his contract) to the new franchise.
        Picks are not roster rows → ignored. Reproducible and no re-scrape needed;
        it fades away on its own once a fresh scrape already reflects the trade."""
        try:
            ov = self._csv("fantasy_trade_overrides.csv")
        except FileNotFoundError:
            return
        ov = ov[ov["player_name"].notna() & (ov["player_name"].astype(str).str.strip() != "")]
        if ov.empty:
            return
        dest = dict(zip(ov["player_name"].map(norm), ov["to_franchise"]))
        mask = self.rosters["key"].isin(dest)
        self.rosters.loc[mask, "nome_franquia"] = self.rosters.loc[mask, "key"].map(dest)

    # ---------- 7-cat valuation ----------
    def _cat_vector(self, df):
        return pd.DataFrame({
            "PTS": df["PTS"].map(_f), "REB": df["TRB"].map(_f), "AST": df["AST"].map(_f),
            "STOCKS": df["STL"].map(_f) + df["BLK"].map(_f),
            "3PM": df["three_p"].map(_f), "PM": df["PM_pg"].map(_f),
            "TOV": -df["TOV"].map(_f),
        })

    # reference-pool floor (z-scores) — single source; predicts/fa_draft read from here
    POOL_MIN_GAMES = 25
    POOL_MIN_MP = 18.0

    def reference_pool(self) -> pd.DataFrame:
        s = self.stats
        return s[(s["G"].map(_f) >= self.POOL_MIN_GAMES)
                 & (s["MP"].map(_f) >= self.POOL_MIN_MP)]

    def _build_value(self):
        s = self.stats
        pool = self.reference_pool()
        cv_pool = self._cat_vector(pool)
        # fillna: without gamelogs (old scrape) the whole pool's PM would be NaN and
        # replace(0,1) doesn't catch NaN → mass-NaN z_PM would silently degrade everything
        mean = cv_pool.mean().fillna(0)
        std = cv_pool.std(ddof=0).replace(0, 1).fillna(1)
        # exposed for whoever needs to DE-normalize z (predicts: minutes sensitivity)
        self.pool_mean, self.pool_std = mean, std
        cv = self._cat_vector(s)
        z = (cv - mean) / std
        z.columns = [f"z_{c}" for c in CATS]
        val = s[["Player", "key", "Pos", "Age", "MP", "G", "three_pa", "three_p_pct", "ft_pct"]].copy()
        val = pd.concat([val, z], axis=1)
        val["z_total"] = z.sum(axis=1)
        val["VA"] = val["z_total"] - val["z_TOV"]          # punt-TOV (includes PM)
        # weighted fit for the Lobos (AST+3PM 1.5x; PM normal weight). NaN z_PM
        # (player without gamelogs) becomes 0 = same semantics as z_total's skipna —
        # otherwise the fit propagates NaN and the player silently vanishes from
        # fa_targets/fa_board
        val["fit"] = (z["z_PTS"] + z["z_REB"] + z["z_STOCKS"] + z["z_PM"].fillna(0)
                      + 1.5 * z["z_AST"] + 1.5 * z["z_3PM"])
        self.val = val.set_index("key")

    # ---------- roster helpers ----------
    def _roster_with_value(self, franchise=None):
        r = self.rosters if franchise is None else self.rosters[self.rosters["nome_franquia"] == franchise]
        j = r.merge(self.val, left_on="key", right_index=True, how="left", suffixes=("", "_v"))
        j["salary_y1_m"] = j["salario_ano1"].map(_f).fillna(0) / 1e6
        return j

    # ---------- public surfaces ----------
    def my_roster(self):
        j = self._roster_with_value(MY_FRANCHISE)
        cols = ["nome_jogador", "posicao_1", "Age", "salary_y1_m", "VA",
                "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV"]
        return (j[cols].rename(columns={"nome_jogador": "Player", "posicao_1": "Pos"})
                .sort_values("VA", ascending=False))

    def league_players(self):
        """Every rostered player in the league (24 franchises) with valuation —
        same view as my_roster(), plus the Franchise column. 👥 Players tab."""
        j = self._roster_with_value()
        cols = ["nome_jogador", "nome_franquia", "posicao_1", "Age", "salary_y1_m",
                "VA", "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV"]
        return (j[cols].rename(columns={"nome_jogador": "Player",
                                        "nome_franquia": "Franchise",
                                        "posicao_1": "Pos"})
                .sort_values("VA", ascending=False))

    def fa_targets(self, top=30):
        paid = set(self.rosters[self.rosters["salario_ano1"].map(_f).fillna(0) > 0]["key"])
        fa_bound = self.rosters[self.rosters["salario_ano1"].map(_f).fillna(0) == 0][["key", "nome_franquia"]]
        holder = dict(zip(fa_bound["key"], fa_bound["nome_franquia"]))
        s = self.stats
        pool = s[(s["G"].map(_f) >= 25) & (s["MP"].map(_f) >= 18)]["key"]
        # $0 players are "FA-bound" (matchable), but the ones on MY team are not targets — already mine
        mine_keys = set(self.rosters[self.rosters["nome_franquia"] == MY_FRANCHISE]["key"])
        avail = [k for k in pool if k not in paid and k not in self.banned
                 and k not in self.restricted and k not in mine_keys]
        v = self.val.loc[[k for k in avail if k in self.val.index]].copy()
        v["held_by"] = [holder.get(k, "(free)") for k in v.index]
        _pg = {"PG": "Guard", "SG": "Guard", "SF": "Wing", "PF": "Forward", "C": "Center"}
        v["Group"] = v["Pos"].str.split("-").str[0].map(_pg).fillna("Wing")
        cols = ["Player", "Pos", "Group", "Age", "VA", "fit",
                "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV", "held_by"]
        return v[cols].sort_values("fit", ascending=False).head(top)

    def draft_board(self, top=25):
        d = self.draft.copy()
        d["key"] = d["nome"].map(norm)
        land = self.landing.set_index("prospect_key")["opportunity_mult"].to_dict() if len(self.landing) else {}
        team = self.landing.set_index("prospect_key")["nba_team_final"].to_dict() if len(self.landing) else {}
        # the projection would come from fct_prospect_scouting (DB). Without the DB,
        # use the college proxy when available.
        d["opp_mult"] = d["key"].map(land).fillna(1.0)
        d["nba_team"] = d["key"].map(team).fillna("?")
        cols = ["nome", "posicao", "posicao_americana", "nba_team", "opp_mult"]
        return (d[cols].rename(columns={"nome": "Prospect", "posicao": "Pos"})
                .sort_values("opp_mult", ascending=False).head(top))

    def league_strength(self):
        rows = []
        for fr, g in self._roster_with_value().groupby("nome_franquia"):
            top = g.dropna(subset=["VA"]).nlargest(10, "VA")
            rows.append({"Franchise": fr, **{c: round(top[f"z_{c}"].sum(), 1) for c in CATS},
                         "Total_VA": round(top["VA"].sum(), 1)})
        df = pd.DataFrame(rows).sort_values("Total_VA", ascending=False).reset_index(drop=True)
        df.insert(0, "Rank", df.index + 1)
        return df

    def team_cap(self):
        r = self._roster_with_value()
        agg = r.groupby("nome_franquia")["salary_y1_m"].sum().round(1)
        df = agg.reset_index().rename(columns={"nome_franquia": "Franchise", "salary_y1_m": "Payroll_M"})
        df["Space_M"] = (CAP - df["Payroll_M"]).round(1)
        return df.sort_values("Space_M", ascending=False).reset_index(drop=True)
