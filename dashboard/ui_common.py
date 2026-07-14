"""
Shared module of the unified dashboard (Bandeja de 3) — extracted in the
app.py + fantasy_gm_tool.py merge (Round 6, Phase 2) to kill duplication:

  - Postgres access with GRACEFUL FALLBACK: DB down → clear warning;
    SQL/schema error → the REAL error surfaces (not masked as "DB down");
    a failure is never cached (only success enters the cache)
  - cached loaders for the seed engine (Engine, FADraft, Predicts) + cached
    wrappers of the heavy methods (avoids recomputing on every widget interaction)
  - display helpers (label translation, z-score colors, show())
"""
from __future__ import annotations
import os

import pandas as pd
import streamlit as st

from fantasy_engine import CATS, MY_FRANCHISE

# ---------- Postgres (dbt marts) with fallback ----------

DB_HINT = ("⚠️ Postgres is down — this tab reads the dbt marts. Start the database "
           "(`make db-up`) and run `make pipeline`. "
           "The seed-based tabs keep working.")

def _db_kw() -> dict:
    # read on EVERY call (not at import): the env can change at runtime (tests,
    # switching databases) and a dict frozen at import would ignore that
    return dict(
        host=os.getenv("DBT_HOST", "localhost"), port=os.getenv("DBT_PORT", "5432"),
        dbname=os.getenv("DBT_DBNAME", "nba"), user=os.getenv("DBT_USER", "postgres"),
        password=os.getenv("DBT_PASSWORD", "postgres"), connect_timeout=3,
    )


@st.cache_resource
def _conn():
    import psycopg2
    return psycopg2.connect(**_db_kw())


@st.cache_data(ttl=15)
def db_alive() -> bool:
    """Short cached ping (15s): every DB tab short-circuits within a single run
    when the database is down (otherwise each query would pay the 3s connect
    timeout)."""
    import psycopg2
    try:
        with psycopg2.connect(**{**_db_kw(), "connect_timeout": 2}) as c:
            c.cursor().execute("select 1")
        return True
    except Exception:
        return False


@st.cache_data(ttl=300)
def _q_ok(sql: str) -> pd.DataFrame:
    """Only SUCCESS enters the cache — exceptions propagate and nothing is
    memoized (a transient failure must not pin the warning for 5 minutes)."""
    return pd.read_sql_query(sql, _conn())


def reset_db_caches():
    """Drops the connection and cached results (used by the smoke test and after
    a database restart). Closes the connection before releasing it (otherwise
    the socket leaks)."""
    try:
        _conn().close()
    except Exception:
        pass
    _conn.clear()
    _q_ok.clear()
    db_alive.clear()


def q(sql: str) -> pd.DataFrame | None:
    """Query against the marts. None = database unavailable (the tab shows
    DB_HINT via db_guard). A SQL/schema error while the database is UP becomes
    an st.error with the real cause — the 'DB down' diagnosis must not mask a
    column typo."""
    if not db_alive():
        return None
    for attempt in (1, 2):
        try:
            return _q_ok(sql)
        except Exception as e:
            # the cached connection may have died (PG restart): recycle it and
            # retry once with a fresh connection before concluding anything
            try:
                _conn().close()
            except Exception:
                pass
            _conn.clear()
            if attempt == 2:
                if db_alive():
                    st.error(f"Query error (the database is UP — likely a mart "
                             f"not built yet or a SQL issue): {e}")
                    return pd.DataFrame()   # sentinel ≠ None: not 'DB down'
                return None
    return None


def db_guard(df: pd.DataFrame | None) -> bool:
    """True if the data arrived and is non-empty; None → standard DB-down warning."""
    if df is None:
        st.warning(DB_HINT)
        return False
    return not df.empty


# ---------- seed engine (always available) ----------

@st.cache_resource
def load_engine():
    from fantasy_engine import Engine
    return Engine()


@st.cache_resource
def load_fadraft():
    from fa_draft_engine import FADraft
    return FADraft(load_engine())


@st.cache_data
def load_advanced():
    fd = load_fadraft()
    wd = fd.simulate_weights()   # dict cat -> Δwinrate (fa_board depends on the weights)
    weights_df = (pd.DataFrame({"category": list(wd.keys()),
                                "dwinrate_weight": list(wd.values())})
                  .sort_values("dwinrate_weight", ascending=False))
    return {
        "weights": weights_df, "base_wr": fd.base_winrate,
        "fa_board": fd.fa_board(30), "rivals": fd.rival_competition(),
        "waiver": fd.waiver_watch(), "curve": fd.pick_curve(),
        "price": fd.pick_price(), "draft2": fd.draft_board2(30),
        "buy": fd.pick_buy_analysis(),
    }


@st.cache_resource
def load_predicts():
    from predicts import Predicts
    return Predicts(load_engine())


# cached wrappers of the heavy methods: the bodies of ALL tabs execute on every
# Streamlit rerun — without this, moving a slider recomputes everything again.

@st.cache_data
def cached_roster_predicts() -> pd.DataFrame:
    return load_predicts().roster_predicts()


@st.cache_data
def cached_team_cat_matrix() -> pd.DataFrame:
    return load_fadraft().team_cat_matrix()


@st.cache_data
def cached_league_strength() -> pd.DataFrame:
    return load_engine().league_strength()


@st.cache_data
def cached_team_cap() -> pd.DataFrame:
    return load_engine().team_cap()


@st.cache_data
def cached_fa_targets(top: int) -> pd.DataFrame:
    return load_engine().fa_targets(top)


@st.cache_data
def cached_my_roster() -> pd.DataFrame:
    return load_engine().my_roster()


@st.cache_data
def cached_league_players() -> pd.DataFrame:
    return load_engine().league_players()


# ---------- display helpers ----------

NOMES = {
    "z_PTS": "Points", "z_REB": "Rebounds", "z_AST": "Assists", "z_STOCKS": "Stl+Blk",
    "z_3PM": "3-Pointers", "z_PM": "Plus/Minus", "z_TOV": "Turnovers", "salary_y1_m": "Salary $M", "VA": "Value",
    "va_over_repl": "Value over repl.", "fit_sim": "Fit", "injury_disc": "Health",
    "ctx_mult": "Context 26-27",
    "score": "Score", "pos_group": "Group", "fit": "Fit", "held_by": "Current holder",
    "curve_proj": "Projection", "opp_mult": "Opportunity", "min_vacuum": "Minutes vacancy",
    "pick_NBA": "NBA Pick", "final_team": "NBA Team", "nba_team": "NBA Team",
    "posicao_americana": "Pos (US)", "free_cap_M": "Free cap $M",
    "weak_cats": "Weak in", "fa_threat": "Bidding threat",
    "likely_cut": "Likely cut", "Total_VA": "Total value",
    "Payroll_M": "Payroll $M", "Space_M": "Cap space $M", "Age": "Age",
}
# derived from NOMES — a single source of truth for the category labels
CAT_LABELS = {c: NOMES[f"z_{c}"] for c in CATS}
ZCOLS = set(CAT_LABELS.values())


def zcolor(v, scale: float = 1.0):
    """Z-score color: 🟩 strong … 🟥 hole. scale adjusts the cutoffs (e.g. scale=4
    for team sums, where ±1/±3 play the role of ±0.25/±0.75)."""
    try:
        v = float(v) / scale
    except (TypeError, ValueError):
        return ""
    if v >= 0.75:  return "background-color:#1b5e20;color:white"   # elite
    if v >= 0.25:  return "background-color:#4caf50"               # good
    if v > -0.25:  return "background-color:#9e9e9e"               # average
    if v > -0.75:  return "background-color:#ef9a9a"               # weak
    return "background-color:#b71c1c;color:white"                  # hole


def highlight_mine(s):
    """Styler that highlights the Lobos row in league tables."""
    return ["background-color:#0d47a1;color:white;font-weight:bold"
            if v == MY_FRANCHISE else "" for v in s]


# categorical palette validated for a dark surface (dataviz skill, 4 slots, PASS
# on luminance band / chroma / CVD / contrast). FIXED order — never cycle it.
RADAR_SERIES = ["#3987e5", "#199e70", "#c98500", "#9085e9"]
RADAR_REF = "#c3c2b7"          # reference outline (Lobos) — neutral, dashed


def radar_chart(profiles: dict, cats: list, reference: str | None = None,
                size: int = 440):
    """Radar of per-category z-scores (pure Altair — no plotly in the project).
    profiles: {name: {cat: z}} — the `reference` item (e.g. Lobos) becomes a
    NEUTRAL dashed outline; the rest get the fixed palette. SQUARE by construction
    (width=height=size — a stretched radar lies when comparing axes).
    r = z clipped to [-1.5, +3] shifted to 0..4.5; the solid ring = league
    average (z=0). TOV arrives already inverted from the engine."""
    import math

    import altair as alt
    import numpy as np

    LO, HI = -1.5, 3.0
    n = len(cats)
    ang = {c: 2 * math.pi * i / n for i, c in enumerate(cats)}

    def xy(c, z):
        r = float(np.clip(z if pd.notna(z) else 0.0, LO, HI)) - LO
        return r * math.sin(ang[c]), r * math.cos(ang[c])

    def poly(name, prof):
        return [{"who": name, "cat": CAT_LABELS.get(c, c),
                 "z": None if pd.isna(prof.get(c)) else round(float(prof.get(c)), 2),
                 "x": xy(c, prof.get(c, 0.0))[0], "y": xy(c, prof.get(c, 0.0))[1],
                 "order": i}
                for i, c in enumerate(cats + cats[:1])]

    players = {k: v for k, v in profiles.items() if k != reference}
    df = pd.DataFrame([r for nm, pf in players.items() for r in poly(nm, pf)])

    grid_rows = []                                     # rings: z=0 (solid) and z=+3
    for z_ring, dash in [(0.0, [1, 0]), (3.0, [4, 4])]:
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            r = z_ring - LO
            grid_rows.append({"ring": f"z{z_ring}", "dash": str(dash),
                              "x": r * math.sin(a), "y": r * math.cos(a), "order": k})
    grid = pd.DataFrame(grid_rows)

    lab_rows = []
    for c in cats:
        x, y = xy(c, HI)
        lab_rows.append({"cat": CAT_LABELS.get(c, c), "x": x * 1.22, "y": y * 1.22})
    labels = pd.DataFrame(lab_rows)

    dom = [-6.0, 6.0]
    enc_x = alt.X("x:Q", axis=None, scale=alt.Scale(domain=dom))
    enc_y = alt.Y("y:Q", axis=None, scale=alt.Scale(domain=dom))

    ring0 = alt.Chart(grid[grid["ring"] == "z0.0"]).mark_line(
        color="#7a7a76", strokeWidth=1.2, opacity=0.8).encode(
        x=enc_x, y=enc_y, order="order:O")
    ring3 = alt.Chart(grid[grid["ring"] == "z3.0"]).mark_line(
        color="#55554f", strokeDash=[4, 4], strokeWidth=1, opacity=0.7).encode(
        x=enc_x, y=enc_y, order="order:O")

    layers = [ring3, ring0]
    if reference and reference in profiles:
        ref_df = pd.DataFrame(poly(reference, profiles[reference]))
        layers.append(alt.Chart(ref_df).mark_line(
            color=RADAR_REF, strokeDash=[7, 5], strokeWidth=2, opacity=0.9).encode(
            x=enc_x, y=enc_y, order="order:O",
            tooltip=[alt.Tooltip("who:N", title=""),
                     alt.Tooltip("cat:N", title="category"),
                     alt.Tooltip("z:Q", title="z")]))
    if len(df):
        color = alt.Color("who:N", title="",
                          scale=alt.Scale(domain=list(players), range=RADAR_SERIES),
                          legend=alt.Legend(orient="top", labelLimit=220))
        tt = [alt.Tooltip("who:N", title=""),
              alt.Tooltip("cat:N", title="category"), alt.Tooltip("z:Q", title="z")]
        layers.append(alt.Chart(df).mark_line(strokeWidth=2, opacity=0.9).encode(
            x=enc_x, y=enc_y, color=color, detail="who:N", order="order:O", tooltip=tt))
        layers.append(alt.Chart(df).mark_point(filled=True, size=55, opacity=1).encode(
            x=enc_x, y=enc_y, color=color, tooltip=tt))
    layers.append(alt.Chart(labels).mark_text(
        fontSize=12, fontWeight="bold", color="#a8a79f").encode(
        x=enc_x, y=enc_y, text="cat:N"))

    ch = layers[0]
    for l in layers[1:]:
        ch = ch + l
    return ch.properties(width=size, height=size).configure_view(stroke=None)


def show(df, cols=None, sort=None, ascending=False, color_z=False, bar=None,
         pct=None, height=None):
    """Applies display labels, selects/sorts columns and colors. bar=column shown
    as a progress bar."""
    d = df.copy()
    if sort and sort in d.columns:
        d = d.sort_values(sort, ascending=ascending)
    if cols:
        d = d[[c for c in cols if c in d.columns]]
    d = d.rename(columns=NOMES)
    zc = [c for c in d.columns if c in ZCOLS] if color_z else []
    for c in pct or []:
        c2 = NOMES.get(c, c)
        if c2 in d.columns:
            d[c2] = (d[c2] * 100).round(0).astype("Int64").astype(str) + "%"
    sty = d.style.map(zcolor, subset=zc) if zc else d.style
    cfg = {}
    if bar and len(d):                       # empty df → min()/max() = NaN breaks the bar
        b = NOMES.get(bar, bar)
        if b in d.columns and d[b].notna().any():
            lo, hi = float(d[b].min()), float(d[b].max())
            if lo < hi:
                cfg[b] = st.column_config.ProgressColumn(
                    b, format="%.1f", min_value=lo, max_value=hi)
    kw = {"width": "stretch", "hide_index": True, "column_config": cfg}
    if height:
        kw["height"] = height
    st.dataframe(sty, **kw)
