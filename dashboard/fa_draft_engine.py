"""
FA/Draft 2.0 — advanced decision layer on top of `fantasy_engine`.

Implements the addendum:
  (g) WEIGHTS FROM SIMULATION — H2H winrate sim → Δwinrate per +1σ per category.
  (e) REAL FA POOL — valued players not rostered across the 24 franchises.
  (f) POSITIONAL VALUE OVER REPLACEMENT — z above the position's replacement level.
  (h) RIVAL COMPETITION — rivals' cap × per-category weakness → urgency.
  (i) WAIVER WATCH — franchises above the roster limit → likely cuts.
  (j) INJURY DISCOUNT — fantasy_injuries applies a discount to the projection.
  (k) CACHE — persists outputs in dashboard/data_cache/.

Data note: the simulation uses the league's 7 cats (PTS/REB/AST/STOCKS/3PM/PM/TOV),
majority = 4 of 7; the +/- comes from the gamelogs via Engine (runbook #34). The
Lobos roster reflects the latest scrape + trade overrides.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

from fantasy_engine import Engine, CATS, MY_FRANCHISE, norm, _f

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")
os.makedirs(CACHE, exist_ok=True)
POS_GROUPS = {"PG": "G", "SG": "G", "SF": "W", "PF": "B", "C": "B"}


def _cache(df: pd.DataFrame, name: str) -> pd.DataFrame:
    df.to_csv(os.path.join(CACHE, name), index=False)
    return df


class FADraft:
    def __init__(self, eng: Engine | None = None, my_team: str = MY_FRANCHISE):
        self.eng = eng or Engine()
        self.my = my_team
        self._injuries = self._load_injuries()

    # ---------- per-team category matrix (top-10 starters) ----------
    def team_cat_matrix(self) -> pd.DataFrame:
        ls = self.eng.league_strength().set_index("Franchise")
        return ls[CATS]

    # ---------- (g) per-category weight simulation ----------
    def h2h_margins(self) -> pd.DataFrame:
        """H2H sim with per-category MARGIN (Round 6, Phase 3): besides the binary
        (I take >=4 of the 7 cats), the z distance between me and each rival per
        cat — separates a comfortable win from a razor-thin one. |margin| <= 2z is
        'razor-thin' (flips with one good/bad week from the opponent). Writes
        h2h_margins.csv."""
        mat = self.team_cat_matrix()
        me = mat.loc[self.my]
        rows = []
        for fr in mat.index:
            if fr == self.my:
                continue
            d = {c: round(float(me[c] - mat.loc[fr, c]), 1) for c in CATS}
            wins = sum(v > 0 for v in d.values())
            close_w = [c for c, v in d.items() if 0 < v <= 2]
            close_l = [c for c, v in d.items() if -2 <= v <= 0]
            rows.append({
                "Franchise": fr, **{f"m_{c}": d[c] for c in CATS},
                "cats_won": wins,
                # 7 cats -> no tie possible (4+ takes it; a tie WITHIN a category
                # is rare enough to ignore in the deterministic run)
                "result": "W" if wins >= 4 else "L",
                "close_wins": ",".join(close_w), "close_losses": ",".join(close_l),
            })
        df = pd.DataFrame(rows).sort_values("cats_won", ascending=False)
        return _cache(df, "h2h_margins.csv")

    def simulate_weights(self, bump: float = 1.0) -> dict:
        """Δwinrate per +bump(σ) in each category for MY team.
        H2H: I win a category if my total > the opponent's total; I win the matchup
        if I take >= 4 of the 7 categories (league rule — doc 06 §3).
        Weight = how much +1σ in a cat raises my winrate."""
        M = self.team_cat_matrix()
        if self.my not in M.index:
            raise ValueError(f"{self.my} is not in the matrix")
        me = M.loc[self.my].copy()
        opps = M.drop(index=self.my)

        def winrate(vec) -> float:
            wins = 0
            for _, opp in opps.iterrows():
                cats_won = sum(1 for c in CATS if vec[c] > opp[c])
                wins += (cats_won >= 4)  # majority of the 7
            return wins / len(opps)

        base = winrate(me)
        weights = {}
        for c in CATS:
            bumped = me.copy(); bumped[c] += bump
            weights[c] = round(winrate(bumped) - base, 4)
        out = pd.DataFrame({"category": CATS,
                            "dwinrate_weight": [weights[c] for c in CATS]}).sort_values(
                            "dwinrate_weight", ascending=False)
        out.attrs["base_winrate"] = base
        _cache(out, "sim_weights.csv")
        self.weights = weights
        self.base_winrate = base
        return weights

    # ---------- (e) real FA pool ----------
    def fa_pool(self, min_games: int = 25, min_mp: float = 18.0) -> pd.DataFrame:
        """Valued FAs outside the rosters and not banned. Filters SMALL SAMPLES:
        the z-score of someone with <min_games is noise (e.g. 6 games turns into
        'elite shooter' by luck). Default cutoff = the valuation's reference pool
        (G>=25, MP>=18)."""
        rostered = set(self.eng.rosters["key"])
        banned = getattr(self.eng, "banned", set())
        val = self.eng.val.reset_index()
        pool = val[~val["key"].isin(rostered) & ~val["key"].isin(banned)].copy()
        pool = pool.dropna(subset=["VA"])
        g = pd.to_numeric(pool["G"], errors="coerce")
        mp = pd.to_numeric(pool["MP"], errors="coerce")
        pool = pool[(g >= min_games) & (mp >= min_mp)]
        pool["pos_group"] = pool["Pos"].str.split("-").str[0].map(POS_GROUPS).fillna("W")
        return pool

    # ---------- (f) replacement level per position ----------
    def replacement_levels(self, pool: pd.DataFrame | None = None) -> dict:
        pool = pool if pool is not None else self.fa_pool()
        rep = {}
        for pg, g in pool.groupby("pos_group"):
            # replacement = ~best available FA at the position (top-3 mean to smooth)
            rep[pg] = round(g.nlargest(3, "VA")["VA"].mean(), 2)
        return rep

    # ---------- (g+f+j) weighted FA board ----------
    def fa_board(self, top: int = 30) -> pd.DataFrame:
        if not hasattr(self, "weights"):
            self.simulate_weights()
        pool = self.fa_pool()
        rep = self.replacement_levels(pool)
        # normalize the simulation weights to sum to 1 (scale comparable to z) —
        # only cats with Δwinrate > 0 matter; PTS/STOCKS (Δ=0) drop out of the fit.
        pos_w = {c: max(self.weights[c], 0) for c in CATS}
        tot = sum(pos_w.values()) or 1.0
        w = {c: pos_w[c] / tot for c in CATS}
        # fit_sim = weighted mean of the player's z in the cats that move my winrate
        zc = {c: f"z_{c}" for c in CATS}
        pool["fit_sim"] = sum(pool[zc[c]] * w[c] for c in CATS)
        # (f) value over replacement: VA minus his position's replacement
        pool["va_over_repl"] = pool["VA"] - pool["pos_group"].map(rep)
        # (j) injury discount (fantasy_injuries, last season's data) +
        # 2026-27 CONTEXT (Phase 4 Improvement B): the nba_context_overrides seed
        # knows about Butler's ACL (0.15) and Vučević's bench role (0.75) — without
        # it the board listed both at the top with "health 100%" (doc 09 §16.7).
        pool["injury_disc"] = pool["key"].map(self._injuries).fillna(1.0)
        ctx = getattr(self.eng, "context", None)
        if ctx is not None and len(ctx):
            pool["ctx_mult"] = pool["key"].map(ctx["role_mult"]).astype(float).fillna(1.0)
        else:
            pool["ctx_mult"] = 1.0
        pool["disc"] = pool["injury_disc"] * pool["ctx_mult"]
        base = 0.5 * pool["va_over_repl"] + 0.5 * pool["fit_sim"]
        # sign-safe multiplier (same rule as predicts._apply_mult): a discount on a
        # NEGATIVE score pushes it further down, it doesn't "improve" a bad player
        pool["score"] = np.where(base >= 0, base * pool["disc"],
                                 base * (2.0 - pool["disc"]))
        cols = ["Player", "Pos", "pos_group", "Age", "VA", "va_over_repl", "fit_sim",
                "injury_disc", "ctx_mult", "score"]
        board = (pool[cols]
                 .sort_values("score", ascending=False).head(top).round(2))
        return _cache(board, "fa_board.csv")

    # ---------- (h) rival competition ----------
    def rival_competition(self) -> pd.DataFrame:
        """Rivals with free cap AND weak in a category will bid for FAs of that cat."""
        cap = self.eng.team_cap().set_index("Franchise")["Space_M"]
        M = self.team_cat_matrix()
        league_mean = M.mean()
        rows = []
        for fr in M.index:
            if fr == self.my:
                continue
            space = cap.get(fr, 0)
            weak = [c for c in CATS if M.loc[fr, c] < league_mean[c] - 3]  # well below the mean
            rows.append({"Franchise": fr, "free_cap_M": round(space, 1),
                         "weak_cats": ", ".join(weak) or "—",
                         "fa_threat": round(max(space, 0) / 40 * len(weak), 2)})
        out = pd.DataFrame(rows).sort_values("fa_threat", ascending=False)
        return _cache(out, "rival_competition.csv")

    # ---------- (i) waiver watch ----------
    def waiver_watch(self) -> pd.DataFrame:
        """Franchises above the roster limit will cut their worst player = free FA."""
        fr = self.eng._csv("fantasy_franchises.csv")
        limit = 15  # typical roster limit (adjustable)
        rv = self.eng._roster_with_value()
        rows = []
        for name, g in rv.groupby("nome_franquia"):
            n = len(g)
            if n > limit:
                worst = g.dropna(subset=["VA"]).nsmallest(n - limit, "VA")
                for _, p in worst.iterrows():
                    rows.append({"Franchise": name, "likely_cut": p["nome_jogador"],
                                 "VA": round(p["VA"], 2)})
        out = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Franchise", "likely_cut", "VA"])
        return _cache(out, "waiver_watch.csv")

    # ==================== DRAFT BOARD 2.0 ====================

    # ---------- (a) pick curve (expected production per slot) ----------
    def pick_curve(self, min_year: int = 2016) -> pd.DataFrame:
        """Average fantasy production per pick number (proxy: pg_pts+trb+ast from
        draft.csv, classes >= min_year). LOESS-ish smoothed (moving average).
        Persisted."""
        d = self.eng._csv("draft.csv")
        d = d[d["draft_year"].map(_f) >= min_year].copy()
        d["fantasy_proxy"] = d["pg_pts"].map(_f) + d["pg_trb"].map(_f) + d["pg_ast"].map(_f)
        d["pick"] = d["pick"].map(_f)
        curve = d.dropna(subset=["pick", "fantasy_proxy"]).groupby("pick")["fantasy_proxy"].mean()
        # 5-pick moving average to smooth out noise
        smooth = curve.reindex(range(1, 61)).interpolate().rolling(5, center=True, min_periods=1).mean()
        out = smooth.reset_index(); out.columns = ["pick", "expected_prod"]
        return _cache(out.round(2), "pick_curve.csv")

    # ---------- (d) real pick price (mined from the trades) ----------
    def pick_price(self) -> pd.DataFrame:
        """Average price of a pick per round — sum of the player value on the OTHER
        side of proposals involving a pick (ano_pick/rodada_pick filled in)."""
        t = self.eng._csv("fantasy_trades.csv")
        props_with_pick = t[t["rodada_pick"].map(_f) > 0]["codigo_proposta"].unique()
        rows = []
        for pid in props_with_pick:
            grp = t[t["codigo_proposta"] == pid]
            picks = grp[grp["rodada_pick"].map(_f) > 0]
            players_val = grp[grp["valor_jogador"].map(_f) > 0]["valor_jogador"].map(_f).sum() / 1e6
            for _, pk in picks.iterrows():
                rows.append({"round": int(_f(pk["rodada_pick"])), "price_M": round(players_val, 1)})
        if not rows:
            return pd.DataFrame(columns=["round", "avg_price_M", "n"])
        df = pd.DataFrame(rows)
        agg = df.groupby("round")["price_M"].agg(["mean", "count"]).reset_index()
        agg.columns = ["round", "avg_price_M", "n"]
        return _cache(agg.round(1), "pick_price.csv")

    # ---------- (b) minutes vacuum per NBA team × position ----------
    def _minutes_occupied(self) -> dict:
        s = self.eng.stats
        s = s.copy()
        s["pos_group"] = s["Pos"].astype(str).str.split("-").str[0].map(POS_GROUPS).fillna("W")
        s["mp"] = s["MP"].map(_f).fillna(0)
        # 2026-27 role ≠ 2025-26 (nba_context_overrides seed): a reserve/injured
        # player occupies less (Vučević 0.75, Butler 0.15); waived players
        # (Team='FA') leave the old team's tally — TRULY vacant minutes. Without
        # this, Vučević would carry his full 2TM minutes into ORL's frontcourt.
        ctx = getattr(self.eng, "context", None)
        if ctx is not None and len(ctx):
            mult = s["key"].map(ctx["role_mult"]).astype(float).fillna(1.0)
            s["mp"] = s["mp"] * mult
        occ = s.groupby(["Team", "pos_group"])["mp"].sum().to_dict()
        return occ

    # ---------- (a)+(b)+(c) draft board ----------
    def draft_board2(self, top: int = 30) -> pd.DataFrame:
        dc = self.eng._csv("fantasy_draft_class.csv")
        dc["key"] = dc["nome"].map(norm)
        dc["pos_group"] = dc["posicao"].astype(str).str.split("-").str[0].map(POS_GROUPS).fillna("W")
        # market pick# from the real 2026 NBA draft (talent signal)
        d26 = self.eng._csv("draft.csv")
        d26 = d26[d26["draft_year"].map(_f) == 2026].copy()
        d26["key"] = d26["player_name"].map(norm)
        pick_of = dict(zip(d26["key"], d26["pick"].map(_f)))
        # curve
        curve = self.pick_curve().set_index("pick")["expected_prod"].to_dict()
        # landing spot (final) + curated opportunity
        try:
            land = self.eng.landing.set_index("prospect_key")
            opp_mult = land["opportunity_mult"].to_dict()
            team_final = land["nba_team_final"].to_dict()
        except Exception:
            opp_mult, team_final = {}, {}
        occ = self._minutes_occupied()
        # prospect's NBA team abbr (draft-night in the seed; used as fallback)
        team_abbr = dict(zip(dc["key"], dc["sigla_franquia_nba"].astype(str)))

        rows = []
        for _, p in dc.iterrows():
            k = p["key"]; pk = pick_of.get(k)
            # (a) projection from the real pick's curve (fallback: median ~pick 30)
            proj = curve.get(round(pk), curve.get(30, 5.0)) if pk else curve.get(30, 5.0)
            # (b) minutes vacuum at team × position (less occupied = more opportunity)
            occ_min = occ.get((team_abbr.get(k, "?"), p["pos_group"]), 240)
            vacuum = max(0.0, (48 * 5 * 0.55) - occ_min) / (48 * 5)  # 0..1 approx
            mult = opp_mult.get(k, 1.0)
            # score = projection × opportunity (curated) × (1 + minutes vacuum)
            score = proj * mult * (1 + 0.5 * vacuum)
            rows.append({
                "Prospect": p["nome"], "Pos": p["posicao"],
                "pick_NBA": int(pk) if pk else None,
                "curve_proj": round(proj, 1),
                "opp_mult": round(mult, 2),
                "min_vacuum": round(vacuum, 2),
                "final_team": team_final.get(k, "?"),
                "score": round(score, 1),
            })
        board = pd.DataFrame(rows).sort_values("score", ascending=False).head(top)
        return _cache(board, "draft_board2.csv")

    # ---------- (c)+(d) is BUYING a pick worth it? (surplus vs real price) ----------
    def pick_buy_analysis(self) -> pd.DataFrame:
        """Crosses expected production per slot (curve) with the real pick price
        (trades). A rookie costs ~$5M/3 years → surplus = production value − cap cost.
        Decides whether it's worth paying $34M(1st)/$14M(2nd) in players to BUY the pick."""
        curve = self.pick_curve().set_index("pick")["expected_prod"]
        price = self.pick_price().set_index("round")["avg_price_M"].to_dict()
        rows = []
        for slot in [1, 3, 5, 10, 15, 20, 30, 45]:
            rnd = 1 if slot <= 30 else 2
            prod = curve.get(slot, np.nan)
            cost = price.get(rnd, np.nan)
            # production "worth" ~ prod (in pts+reb+ast); a rookie costs ~$5M of cap (cheap)
            rows.append({
                "pick": slot, "round": rnd,
                "expected_prod": round(prod, 1),
                "pick_cost_M": cost,                     # price in players to buy it
                "rookie_salary_M": 5.0 if rnd == 1 else 2.5,
                "worth_buying": "YES" if (prod >= 14 and rnd == 1) or (prod >= 9 and rnd == 2)
                                else "only if cheap",
            })
        return _cache(pd.DataFrame(rows), "pick_buy_analysis.csv")

    # ---------- runs everything and persists (for the app/report) ----------
    def build_all(self):
        self.simulate_weights(); self.h2h_margins(); self.fa_board()
        self.rival_competition(); self.waiver_watch(); self.pick_curve()
        self.pick_price(); self.draft_board2(); self.pick_buy_analysis()
        return sorted(os.listdir(CACHE))

    # ---------- (j) injuries ----------
    def _load_injuries(self) -> dict:
        try:
            inj = self.eng._csv("fantasy_injuries.csv")
        except FileNotFoundError:
            return {}
        disc = {}
        for _, r in inj.iterrows():
            k = norm(r.get("nome_jogador", ""))
            sit = str(r.get("situacao", "")).lower()
            # discount: day-to-day -0.05, weeks -0.20, season -0.60
            # (seed values are in Portuguese: 'temporada'=season, 'semana'=week)
            if "temporada" in sit or "season" in sit:
                disc[k] = 0.4
            elif "semana" in sit or "week" in sit:
                disc[k] = 0.8
            else:
                disc[k] = 0.95
        return disc
