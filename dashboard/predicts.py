"""
Predicts v2 (Round 6, Phase 1) — consolidates the per-player predictive metrics
into a reproducible artifact (they used to live in ad-hoc /tmp scripts, lost).

Per player of the roster (or of any franchise):
  - VA 2025-26 (punt-TOV, from the Engine) + z per category
  - Floor / Ceiling / Risk(CV)        — game-by-game gamelogs (doc 01 §2.3)
  - Minutes sensitivity @24/28/32     — per-minute rates re-projected on the pool
  - Minutes Upside                    — VA@32 − VA@current MP
  - Usage Upside                      — high TS% + low USG% = hidden possessions
  - Aging curve                       — multiplier per age (2025-26 cross-section,
                                        sanity-checked by draft.csv experience)
  - Development                       — VA − (age−27)·0.35 (doc 01 §2.3)
  - Dynasty                           — mean projected VA over the next 3 years
  - 2026-27 context                   — role_mult from the nba_context_overrides seed
  - Projected VA 2026-27              — VA(adjusted minutes) × aging × context
  - sample_flag                       — G<25 = noise (don't trust the z)

Usage:
    from fantasy_engine import Engine
    from predicts import Predicts
    p = Predicts(Engine())
    p.roster_predicts()          # DataFrame of my roster (writes data_cache/predicts_v2.csv)
    p.aging_curve()              # age -> multiplier curve
    python predicts.py           # smoke: table + 4 directional validation cases
"""
from __future__ import annotations
import os

import numpy as np
import pandas as pd

from fantasy_engine import Engine, CATS, MY_FRANCHISE, norm, _f

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")

# Categories that score points in the punt-TOV build (TOV ignored by build decision).
# VALUE_CATS feeds VA/minutes sensitivity (includes PM — runbook #34);
# SCORE_CATS is counting-only (floor/ceiling/CV): PM is signed and with it the
# per-game score would cross zero, destabilizing the CV (std/mean).
VALUE_CATS = ["PTS", "REB", "AST", "STOCKS", "3PM", "PM"]
SCORE_CATS = ["PTS", "REB", "AST", "STOCKS", "3PM"]
GAMELOG_COLS = {"PTS": "PTS", "REB": "TRB", "AST": "AST", "3PM": "three_p"}
MIN_GAMES_TRUST = 25          # below this, the z-score is noise (sample_flag)
DEV_SLOPE = 0.35              # Development = VA − (age−27)·0.35 (doc 01 §2.3)
PEAK_AGES = (26, 27, 28)      # aging-curve peak (normalizer)


class Predicts:
    def __init__(self, eng: Engine | None = None):
        self.eng = eng or Engine()
        self._gl = None
        self._adv = None
        self._curve = None

    # ---------- sources ----------
    def _gamelogs(self) -> pd.DataFrame:
        if self._gl is None:
            gl = pd.read_csv(os.path.join(self.eng.seeds, "player_gamelogs.csv"),
                             low_memory=False)
            gl["key"] = gl["player_name"].map(norm)
            for c in ["PTS", "TRB", "AST", "STL", "BLK", "three_p", "TOV"]:
                gl[c] = gl[c].map(_f)
            gl["STOCKS"] = gl["STL"] + gl["BLK"]
            # precompute whatever is player-independent — without this each
            # player pays a full-column std() + a scan of the 26k games
            self._gl_std = {c: gl[GAMELOG_COLS.get(c, c)].std(ddof=0) or 1.0
                            for c in SCORE_CATS}
            self._gl_by_key = dict(tuple(gl.groupby("key")))
            self._gl = gl
        return self._gl

    def _advanced(self) -> pd.DataFrame:
        if self._adv is None:
            adv = pd.read_csv(os.path.join(self.eng.seeds, "players_advanced_stats.csv"))
            adv["key"] = adv["Player"].map(norm)
            adv = adv.sort_values("G", key=lambda s: s.map(_f), ascending=False)
            self._adv = adv.drop_duplicates("key", keep="first").set_index("key")
        return self._adv

    # ---------- aging curve ----------
    # PARAMETRIC curve (peak 26-28, accelerating decline >30). Why not 100%
    # empirical: the 2025-26 cross-section suffers from survivorship (at 33+ only
    # the good ones stay in the league → the per-age median does NOT drop; see
    # aging_curve_empirical), and draft.csv only has career aggregates (no
    # age×season pairs). Both serve as a SHAPE sanity-check: the young ramp
    # (~0.90 at 21-22) matches draft.csv's years-in-league curve (exp-2 median
    # ≈ 0.90×peak of exp-8), and the post-30 decline comes from the delta-method
    # literature (Phase 4 may recalibrate).
    AGING = {19: 0.85, 20: 0.88, 21: 0.91, 22: 0.94, 23: 0.96, 24: 0.98,
             25: 0.99, 26: 1.00, 27: 1.00, 28: 1.00, 29: 0.99, 30: 0.97,
             31: 0.95, 32: 0.92, 33: 0.89, 34: 0.85, 35: 0.81, 36: 0.77,
             37: 0.73, 38: 0.69, 39: 0.65, 40: 0.61, 41: 0.57}

    def aging_curve(self) -> pd.Series:
        if self._curve is None:
            self._curve = pd.Series(self.AGING, name="mult").rename_axis("Age")
        return self._curve

    def aging_curve_empirical(self) -> pd.Series:
        """Median (smoothed) production score per age in the 2025-26 cross-section,
        normalized by the 26-28 peak. NOT used in the projection — evidence of the
        cross-sectional cut's limitation (survivorship flattens the decline)."""
        s = self.eng.stats
        pool = s[(s["G"].map(_f) >= MIN_GAMES_TRUST) & (s["MP"].map(_f) >= 18)].copy()
        pool["Age"] = pool["Age"].map(_f)
        cv = self.eng._cat_vector(pool)
        prod = sum(cv[c] / (cv[c].std(ddof=0) or 1.0) for c in SCORE_CATS)
        pool = pool.assign(prod=prod.values)
        med = pool.groupby(pool["Age"].astype(int))["prod"].median()
        med = med.rolling(3, center=True, min_periods=1).mean()
        peak = med.loc[[a for a in PEAK_AGES if a in med.index]].max()
        return (med / peak).round(3)

    def _age_mult(self, age: float, years_ahead: int = 1) -> float:
        """curve(age+k)/curve(age), clipped — one aging step."""
        if pd.isna(age):
            return 1.0
        c = self.aging_curve()
        lo, hi = c.index.min(), c.index.max()
        a0 = int(np.clip(age, lo, hi))
        a1 = int(np.clip(age + years_ahead, lo, hi))
        return float(np.clip(c.loc[a1] / c.loc[a0], 0.75, 1.15))

    def validate_aging_on_draft(self) -> pd.DataFrame:
        """Sanity-check of the curve's shape with draft.csv (longitudinal by cohort):
        career production (pg_pts+pg_trb+pg_ast) by years-since-draft.
        It's not age×season (draft.csv only has career aggregates), but it shows the
        ramp up to the ~5-9 years-in-league window (age ~24-28) and the drop after."""
        d = pd.read_csv(os.path.join(self.eng.seeds, "draft.csv"))
        d = d[d["career_games"].map(_f) >= 100].copy()
        d["exp"] = 2026 - d["draft_year"].map(_f)
        d["prod"] = d["pg_pts"].map(_f) + d["pg_trb"].map(_f) + d["pg_ast"].map(_f)
        out = (d[(d["exp"] >= 1) & (d["exp"] <= 20)]
               .groupby(d["exp"].astype(int))["prod"].agg(["median", "count"]))
        return out.rename(columns={"median": "median_prod", "count": "n"})

    # ---------- per-game metrics (gamelogs) ----------
    def _pergame_scores(self, key: str) -> pd.Series | None:
        """Punt-TOV fantasy score per game: sum of stat/σ_pool over the 5 scoring
        categories (not mean-centered → positive score, stable CV)."""
        self._gamelogs()
        g = self._gl_by_key.get(key)
        if g is None or len(g) < 5:
            return None
        score = sum(g[GAMELOG_COLS.get(c, c)] / self._gl_std[c] for c in SCORE_CATS)
        return score.dropna()

    # ---------- minutes sensitivity ----------
    def _va_at_minutes(self, row: pd.Series, minutes: float) -> float:
        """Punt-TOV VA if the player plays `minutes`/game: per-minute rate ×
        target minutes, re-standardized against the season's per-game pool.
        Linear approximation (constant rate) — slightly overestimates on big
        minute jumps (long rotations tire out), hence the scenarios stop at 32."""
        mp = _f(row["MP"])
        if not mp or mp <= 0:
            return np.nan
        va = 0.0
        for c in VALUE_CATS:
            z_c = row[f"z_{c}"]
            if pd.isna(z_c):        # NaN z_PM (no gamelogs) = neutral contribution,
                continue            # like z_total's skipna — doesn't erase VA@min
            mean_c, std_c = self._pool_mean_std[c]
            pg = z_c * std_c + mean_c            # per-game average implied by the z
            proj = pg / mp * minutes
            va += (proj - mean_c) / std_c
        return va

    @staticmethod
    def _apply_mult(va: float, mult: float) -> float:
        """SIGN-SAFE discount/bonus multiplier. VA is centered around ~0 and goes
        negative — `va * 0.15` on a -2 VA would say that losing the season
        IMPROVES a bad player (-2 → -0.3). Rule: a discount on a negative VA
        pushes it DOWN in the same proportion (va * (2 - mult))."""
        if pd.isna(va) or pd.isna(mult):
            return np.nan
        return va * mult if va >= 0 else va * (2.0 - mult)

    def _project_va(self, v: pd.Series, mp: float, role_mult: float,
                    ctx, aging: float) -> float:
        """Projected VA 2026-27. Two regimes (change_type validated in the Engine):
        - injury: role_mult is AVAILABILITY (fraction of the season) → discounts
          the VA at the current minutes level. Butler 0.15 ⇒ season value ≈ 0,
          without inventing a 5-min/game player.
        - trade/role: role_mult adjusts MINUTES per game (bench↓/starter↑) and the
          VA is recomputed at that level."""
        if not mp or pd.isna(mp):
            return np.nan
        change = str(ctx["change_type"]) if ctx is not None else ""
        if change == "injury":
            return self._apply_mult(
                self._apply_mult(self._va_at_minutes(v, mp), role_mult), aging)
        proj_min = float(np.clip(mp * role_mult, 8, 36))
        return self._apply_mult(self._va_at_minutes(v, proj_min), aging)

    @property
    def _pool_mean_std(self):
        # z DE-normalization uses the SAME pool as Engine._build_value — if the
        # pool floor changes there, the z inverts against the right pool here.
        if not hasattr(self, "_pms"):
            self._pms = {c: (self.eng.pool_mean[c], self.eng.pool_std[c] or 1.0)
                         for c in VALUE_CATS}
        return self._pms

    # ---------- consolidation ----------
    def roster_predicts(self, franchise: str = MY_FRANCHISE) -> pd.DataFrame:
        eng = self.eng
        r = eng.rosters[eng.rosters["nome_franquia"] == franchise]
        adv = self._advanced()
        usg_med = adv["usg_pct"].map(_f).median()   # loop invariants
        ts_med = adv["ts_pct"].map(_f).median()
        rows = []
        for _, rr in r.iterrows():
            key = rr["key"]
            if key not in eng.val.index:
                rows.append({"Player": rr["nome_jogador"], "Pos": rr["posicao_1"],
                             "sample_flag": "no NBA stats (rookie?)"})
                continue
            v = eng.val.loc[key]
            age, g, mp = _f(v["Age"]), _f(v["G"]), _f(v["MP"])
            va = float(v["VA"])          # the single definition of VA lives in the Engine

            sc = self._pergame_scores(key)
            floor = float(np.percentile(sc, 20)) if sc is not None else np.nan
            ceil = float(np.percentile(sc, 85)) if sc is not None else np.nan
            cv = float(sc.std(ddof=0) / sc.mean()) if sc is not None and sc.mean() > 0 else np.nan

            va24, va28, va32 = (self._va_at_minutes(v, m) for m in (24, 28, 32))
            va_now_m = self._va_at_minutes(v, mp)
            min_up = va32 - va_now_m if not pd.isna(va32) else np.nan

            usg = _f(adv.loc[key, "usg_pct"]) if key in adv.index else np.nan
            ts = _f(adv.loc[key, "ts_pct"]) if key in adv.index else np.nan
            usage_up = (max(0.0, (ts - ts_med) * 10) if not pd.isna(ts) and not pd.isna(usg)
                        and usg < usg_med else 0.0)

            ctx = eng.context.loc[key] if key in eng.context.index else None
            role_mult = _f(ctx["role_mult"]) if ctx is not None else 1.0
            role_note = str(ctx["role_2026_27"]) if ctx is not None else ""

            aging = self._age_mult(age, 1)
            dev = va - (age - 27) * DEV_SLOPE if not pd.isna(age) else np.nan
            va_proj = self._project_va(v, mp, role_mult, ctx, aging)
            # dynasty: mean projected VA over t+1..t+3 — _age_mult(age+1, k) is
            # already the cumulative ratio curve(age+1+k)/curve(age+1); role = year 1's
            dyn = np.nan
            if not pd.isna(va_proj):
                dyn = float(np.mean([self._apply_mult(va_proj, self._age_mult(age + 1, k))
                                     for k in range(3)]))

            rows.append({
                "Player": v["Player"], "Pos": v["Pos"], "Age": age, "G": g, "MP": mp,
                "VA_2526": round(va, 2), "Floor": round(floor, 1), "Ceiling": round(ceil, 1),
                "CV": round(cv, 2) if not pd.isna(cv) else np.nan,
                "VA@24": round(va24, 2), "VA@28": round(va28, 2), "VA@32": round(va32, 2),
                "MinutesUpside": round(min_up, 2) if not pd.isna(min_up) else np.nan,
                "UsageUpside": round(usage_up, 2),
                "aging_mult": round(aging, 3), "Development": round(dev, 2),
                "role_mult": role_mult, "context_2627": role_note,
                "VA_proj_2627": round(va_proj, 2) if not pd.isna(va_proj) else np.nan,
                "Dynasty": round(dyn, 2) if not pd.isna(dyn) else np.nan,
                "sample_flag": "⚠️ G<25 = noise" if g and g < MIN_GAMES_TRUST else "",
            })
        df = pd.DataFrame(rows).sort_values("VA_proj_2627", ascending=False, na_position="last")
        if franchise == MY_FRANCHISE:   # the persisted artifact is MY roster;
            os.makedirs(CACHE, exist_ok=True)   # rival predicts don't overwrite it
            df.to_csv(os.path.join(CACHE, "predicts_v2.csv"), index=False)
        return df

    # ---------- directional validation (Round 6 brief) ----------
    def validation_cases(self) -> pd.DataFrame:
        """4 cases with a known direction: Butler≈0 (ACL), Vučević↓ (bench),
        Claxton↑ (~+1, starter), Ware↑ (rebuild)."""
        cases = ["Jimmy Butler", "Nikola Vučević", "Nic Claxton", "Kel'el Ware"]
        out = []
        for name in cases:
            key = norm(name)
            if key not in self.eng.val.index:
                continue
            v = self.eng.val.loc[key]
            va = float(v["VA"])
            ctx = self.eng.context.loc[key] if key in self.eng.context.index else None
            role_mult = _f(ctx["role_mult"]) if ctx is not None else 1.0
            mp = _f(v["MP"])
            va_proj = self._project_va(v, mp, role_mult, ctx,
                                       self._age_mult(_f(v["Age"]), 1))
            out.append({"Player": v["Player"], "VA_2526": round(va, 2),
                        "role_mult": role_mult,
                        "VA_proj_2627": round(va_proj, 2),
                        "delta": round(va_proj - va, 2)})
        return pd.DataFrame(out)


if __name__ == "__main__":
    p = Predicts()
    print("=== Predicts v2 — Lobos Comunistas ===")
    print(p.roster_predicts().to_string(index=False))
    print("\n=== Directional validation cases ===")
    print(p.validation_cases().to_string(index=False))
    print("\n=== Parametric aging curve (age -> mult) ===")
    print(p.aging_curve().round(3).to_string())
    print("\n=== Empirical aging curve 2025-26 (evidence only; survivorship) ===")
    print(p.aging_curve_empirical().to_string())
    print("\n=== draft.csv sanity-check (production × years in the league) ===")
    print(p.validate_aging_on_draft().to_string())
