"""
Unified Bandeja de 3 dashboard — Streamlit (merge of app.py + fantasy_gm_tool.py,
Round 6 Phase 2). ONE entrypoint:

    streamlit run dashboard/app.py    →  http://localhost:8501

Two tab families:
  - SEEDS (always work, no database): My Team, Predicts, War, FA, Draft,
    League, Salaries — `fantasy_engine`/`fa_draft_engine`/`predicts` engine.
  - dbt MARTS (need Postgres): NBA Averages, NBA Value, College, Scouting,
    Comps — without the database they show a clear warning (never a stacktrace).

Headless smoke test of every tab: python dashboard/test_app_smoke.py
"""
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fantasy_engine import CATS, MY_FRANCHISE
from news import get_nba_news, tag_players
from ui_common import (CAT_LABELS, NOMES, cached_fa_targets, cached_league_players,
                       cached_league_strength,
                       cached_my_roster, cached_roster_predicts, cached_team_cap,
                       cached_team_cat_matrix, db_guard, highlight_mine,
                       load_advanced, load_engine, load_predicts, q, show, zcolor)

st.set_page_config(page_title="Bandeja de 3", layout="wide")

eng = load_engine()
adv = load_advanced()

st.title("🏀 Bandeja de 3 — Lobos GM Headquarters")
st.caption("How to read the numbers: **Value / Score** — the higher, the better. "
           "**Colored categories** — 🟩 green = strong · 🟥 red = weak.")

(tab_time, tab_players, tab_pred, tab_war, tab_fa2, tab_draft2, tab_fa, tab_draft,
 tab_liga, tab_cap, tab_nba1, tab_nba2, tab_coll, tab_scout, tab_comps,
 tab_news) = st.tabs([
    "🧢 My Team", "👥 Players", "🔮 Predicts", "⚔️ War", "🎯 Free Agency",
    "🏆 Draft", "🔎 FA (raw list)", "🔎 Draft (raw list)", "🏅 League",
    "💰 Salaries", "📊 NBA Averages", "💎 NBA Value", "🎓 College", "🔭 Scouting",
    "🧬 Comps", "📰 News",
])

# ---------- MY TEAM (seeds) ----------
with tab_time:
    st.subheader(f"Roster — {MY_FRANCHISE}")
    mr = cached_my_roster()
    try:
        fc = pd.read_csv(os.path.join(eng.seeds, "fantasy_contracts.csv"))
        roster_names = set(pd.read_csv(os.path.join(eng.seeds, "my_roster.csv"))
                           ["player_name"].str.lower())
        fc = fc[fc["player_name"].str.lower().isin(roster_names)]  # orphan contract
        caps = st.columns(3)                                       # doesn't count on the cap
        for col, yr, lab in zip(caps, ["salary_y1", "salary_y2", "salary_y3"],
                                ["Year 1", "Year 2", "Year 3"]):
            col.metric(f"Cap {lab}", f"${fc[yr].fillna(0).sum()/1e6:.1f}M")
    except Exception as e:      # a missing/corrupt seed must not take the tab down
        st.caption(f"(contracts unavailable: {e})")
    prof = pd.DataFrame({
        "Category": [CAT_LABELS[c] for c in CATS],
        "Team strength": [round(mr[f"z_{c}"].dropna().nlargest(10).mean(), 2) for c in CATS],
    }).sort_values("Team strength")
    st.markdown("#### Where the team is strong and weak")
    st.caption("Bar to the **right** = you win that category against the league. To the "
               "**left** = needs reinforcement. (0 = league average.)")
    st.bar_chart(prof.set_index("Category"), horizontal=True, color="#42a5f5")
    fraca = prof.iloc[0]["Category"]
    st.info(f"🎯 Your biggest hole today: **{fraca}** — prioritize it in FA and the draft.")
    st.markdown("#### Roster (green = crushes the category · red = weak)")
    show(mr, cols=["Player", "Pos", "Age", "salary_y1_m", "VA",
                   "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV"],
         sort="VA", color_z=True, bar="VA", height=680)
    rookies = mr[mr["VA"].isna()]["Player"].tolist()
    if rookies:
        st.markdown("#### Rookies / no NBA stats → see the **🔭 Scouting** tab")
        st.write(", ".join(rookies))
    with st.expander("7-cat view with +/- and games (dbt mart fct_my_roster)"):
        r7 = q("""
            select player_name, positions, games_played, z_total,
                   z_pts, z_trb, z_ast, z_stocks, z_three_p, z_plus_minus, z_tov
            from analytics_marts.fct_my_roster where has_nba_value
        """)
        if db_guard(r7):
            st.dataframe(r7.sort_values("z_total", ascending=False),
                         width="stretch", hide_index=True)

# ---------- PLAYERS (seeds) ----------
with tab_players:
    st.subheader("👥 League players — every rostered player")
    st.caption("Same heatmap as **My Team**, for all 24 franchises: "
               "🟩 green = strong in the category · 🟥 red = weak. "
               "Players without a valuation (rookies/no NBA stats) get no color.")
    lp = cached_league_players()
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    franquias = fc1.multiselect("Franchise", sorted(lp["Franchise"].unique()),
                                placeholder="All franchises")
    posicoes = ["All"] + sorted(lp["Pos"].dropna().unique().tolist())
    pos = fc2.selectbox("Position", posicoes, key="players_pos")
    busca = fc3.text_input("Search player", key="players_busca")
    filt = lp
    if franquias:
        filt = filt[filt["Franchise"].isin(franquias)]
    if pos != "All":
        filt = filt[filt["Pos"] == pos]
    if busca.strip():
        filt = filt[filt["Player"].str.contains(busca.strip(), case=False, na=False)]
    st.caption(f"{len(filt)} players · {filt['Franchise'].nunique()} franchises")
    show(filt, cols=["Player", "Franchise", "Pos", "Age", "salary_y1_m", "VA",
                     "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV"],
         sort="VA", color_z=True, bar="VA", height=680)

# ---------- PREDICTS (seeds; Phase 1) ----------
with tab_pred:
    st.subheader("🔮 Predicts v2 — 2026-27 roster projection")
    st.caption("Projected VA = minutes adjusted for the 2026-27 role (per-row source in the "
               "`nba_context_overrides` seed) × aging curve. **⚠️ G<25 = noisy sample.** "
               "Floor/Ceiling = 20th/85th percentiles of the per-game score; CV = risk (volatility).")
    p = load_predicts()
    pred = cached_roster_predicts()
    c1, c2, c3 = st.columns(3)
    ok = pred["VA_proj_2627"].dropna()
    c1.metric("Projected roster VA (sum)", f"{ok.sum():.1f}")
    c2.metric("Best projection", f"{pred.iloc[0]['Player']} ({pred.iloc[0]['VA_proj_2627']})")
    ruido = int((pred["sample_flag"].astype(str).str.len() > 0).sum())
    c3.metric("Players with a noisy sample", ruido)
    st.markdown("#### Consolidated table (sorted by the 2026-27 projection)")
    st.dataframe(pred, width="stretch", hide_index=True, height=620)
    cA, cB = st.columns(2)
    with cA:
        st.markdown("#### Minutes sensitivity (@24 → @32)")
        sens = pred.dropna(subset=["VA@24"]).set_index("Player")[["VA@24", "VA@28", "VA@32"]]
        st.dataframe(sens.style.map(zcolor), width="stretch", height=400)
    with cB:
        st.markdown("#### Aging curve in use")
        st.caption("Parametric (peak 26-28, decline >30) — see doc 09 §15.3.")
        st.line_chart(p.aging_curve(), height=300)
        with st.expander("Directional validation cases (Butler/Vučević/Claxton/Ware)"):
            st.dataframe(p.validation_cases(), hide_index=True)

# ---------- WAR (seeds) ----------
with tab_war:
    st.subheader("⚔️ War — you against any rival, category by category")
    mat = cached_team_cat_matrix()
    rivals = [f for f in mat.index if f != MY_FRANCHISE]
    rival = st.selectbox("Rival", rivals)
    me, rv = mat.loc[MY_FRANCHISE], mat.loc[rival]
    diff = (me - rv).round(1)
    wins = int(sum(diff[c] > 0 for c in CATS))
    c1, c2, c3 = st.columns(3)
    c1.metric("Categories you win", f"{wins} of {len(CATS)}")
    c2.metric("Matchup result",   # 7 cats: 4+ takes it, no tie possible
              "✅ WIN" if wins >= 4 else "❌ LOSS")
    closest = diff.abs().idxmin()
    c3.metric("Tightest category", f"{CAT_LABELS.get(closest, closest)} ({diff[closest]:+.1f}z)")
    st.caption("Margin = difference in the sum of z-scores of each roster's top 10. "
               "|margin| < 2z ≈ flips with one good/bad week — that's where the variance lives. "
               "TOV counts in the matchup (league rule), even with our punt-TOV build. "
               "Margin 0.0 = tie IN the category — the league's tiebreak rule is unknown; "
               "here it counts as a non-win (conservative reading).")
    comp = pd.DataFrame({"You": me[CATS].values, rival: rv[CATS].values,
                         "Margin": diff[CATS].values},
                        index=[CAT_LABELS[c] for c in CATS])
    st.markdown("#### Margin per category (positive = you win)")
    st.bar_chart(comp["Margin"], horizontal=True, color="#ef5350")
    st.dataframe(comp.style.map(zcolor, subset=["Margin"]), width="stretch")
    perigo = [CAT_LABELS[c] for c in CATS if 0 < diff[c] <= 2]
    if perigo:
        st.warning(f"🔥 Razor-thin wins (≤2z): **{', '.join(perigo)}** — shoring up these "
                   "categories is what protects the matchup against weekly variance.")

# ---------- FREE AGENCY 2.0 (seeds) ----------
with tab_fa2:
    st.subheader("🎯 Best Free Agency targets")
    st.markdown("#### How much each category is worth FOR YOUR wins")
    st.caption("Bigger bar = winning that category gives you more wins. It's what the ranking prioritizes.")
    w = adv["weights"].copy()
    w["Win gain"] = (w["dwinrate_weight"] * 100).round(1)
    w["Category"] = w["category"]
    st.bar_chart(w.set_index("Category")["Win gain"], horizontal=True, color="#66bb6a")
    top_lever = w.sort_values("dwinrate_weight", ascending=False).iloc[0]
    c1, c2 = st.columns(2)
    c1.metric("Chance of winning a matchup today", f"{adv['base_wr']*100:.0f}%")
    c2.metric("Category that wins you the most", top_lever["category"],
              f"+{top_lever['dwinrate_weight']*100:.0f}pp per upgrade")
    st.divider()
    st.markdown("#### Target ranking (free agents in the league, weighted by what you need)")
    st.caption("**Score** = player value + fit with what's missing − injury risk. "
               "**Health** = 100% means no injury.")
    show(adv["fa_board"], cols=["Player", "Pos", "Age", "score", "VA", "va_over_repl",
                                "injury_disc", "ctx_mult"],
         sort="score", bar="score", pct=["injury_disc", "ctx_mult"], height=560)
    with st.expander("⚔️ Who's fighting hardest for the SAME targets as you (rivals)"):
        show(adv["rivals"], cols=["Franchise", "free_cap_M", "weak_cats", "fa_threat"],
             sort="free_cap_M")
    with st.expander("🔔 Overstuffed teams that will CUT good players (waiver)"):
        show(adv["waiver"], cols=["Franchise", "likely_cut", "VA"], sort="VA")

# ---------- DRAFT 2.0 (seeds) ----------
with tab_draft2:
    st.subheader("🏆 2026 Draft Board (talent × opportunity)")
    st.caption("**Score** combines: NBA draft position + a team that gives minutes (rebuild) + the open slot on your roster.")
    d2 = adv["draft2"].copy()
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        st.markdown("#### Top 15 prospects (by Score)")
        top15 = d2.sort_values("score", ascending=False).head(15)
        st.bar_chart(top15.set_index("Prospect")["score"], horizontal=True, color="#ab47bc")
    with cc2:
        st.markdown("#### Value × draft position")
        st.caption("High on a late pick = **sleeper**; low on a high pick = risk.")
        sc = d2[d2["pick_NBA"].notna()].rename(columns={"pick_NBA": "NBA Pick", "score": "Score"})
        st.scatter_chart(sc, x="NBA Pick", y="Score", color="#ab47bc", height=340)
    st.markdown("#### Full board")
    show(d2, cols=["Prospect", "Pos", "pick_NBA", "final_team", "score", "curve_proj",
                   "opp_mult", "min_vacuum"], sort="score", bar="score", height=380)
    st.divider()
    st.markdown("#### Is BUYING a pick in a trade worth it?")
    st.caption("Expected production of the pick × real price (in players) from the league's trades.")
    buy = adv["buy"].rename(columns={
        "pick": "Pick #", "round": "Round", "expected_prod": "Expected production",
        "pick_cost_M": "Cost in players $M", "rookie_salary_M": "Rookie salary $M",
        "worth_buying": "Worth buying?"})
    st.dataframe(
        buy.style.map(lambda v: "background-color:#1b5e20;color:white" if v == "YES"
                      else "background-color:#5d4037" if v == "only if cheap" else "",
                      subset=["Worth buying?"]),
        width="stretch", hide_index=True)
    st.info("💡 Rule of thumb: a 1st-round pick costs ~**$34M** in players — only worth it in the "
            "**top ~15**. Late 1st: only at a discount. A 2nd-rounder (~$14M) pays off nicely.")

# ---------- FA raw list (seeds) ----------
with tab_fa:
    st.subheader("Free Agency — raw list (every aspect)")
    st.caption("**Current holder** = franchise holding the rights (can match the offer if it's "
               "in the playoffs); '(free)' = no holder.")
    fa = cached_fa_targets(120)
    ASPECTOS = {"VA": "Overall value", "fit": "Punt-TOV fit",
                **{f"z_{c}": CAT_LABELS[c] for c in CATS}}
    c1, c2, c3 = st.columns(3)
    grupos = c1.multiselect("Position", ["Guard", "Wing", "Forward", "Center"], default=[])
    ordenar = c2.selectbox("Sort by (the aspect you care about)", list(ASPECTOS),
                           format_func=lambda k: ASPECTOS[k])
    min_va = c3.slider("Minimum value (cuts the weak)", -3.0, 8.0, -1.0, 0.5)
    if grupos:
        fa = fa[fa["Group"].isin(grupos)]
    fa = fa[fa["VA"] >= min_va]
    fa_sorted = fa.sort_values(ordenar, ascending=False)
    st.caption(f"{len(fa)} free/matchable players (sample ≥25 games). "
               f"Sorted by **{ASPECTOS[ordenar]}**.")
    viz = st.radio("View", ["🔥 Heatmap (table)", "🕸️ Radar (compare)"],
                   horizontal=True, key="fa_viz")
    if viz.startswith("🔥"):
        show(fa, cols=["Player", "Pos", "Group", "Age", "VA", "fit",
                       "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV",
                       "held_by"],
             sort=ordenar, color_z=True, height=560)
    else:
        from ui_common import radar_chart
        opts = fa_sorted["Player"].tolist()
        escolhidos = st.multiselect("Compare up to 4 targets", opts, default=opts[:2],
                                    max_selections=4, key="fa_radar_sel")
        com_time = st.checkbox("Overlay the Lobos (top-10 z average)", value=True,
                               key="fa_radar_me")
        REF = "🐺 Lobos (top-10)"
        profiles = {}
        if com_time:
            mr = cached_my_roster()
            profiles[REF] = {c: float(mr[f"z_{c}"].dropna().nlargest(10).mean())
                             for c in CATS}
        for _, r in fa_sorted[fa_sorted["Player"].isin(escolhidos)].iterrows():
            profiles[r["Player"]] = {c: r[f"z_{c}"] for c in CATS}
        if escolhidos:
            _, mid, _ = st.columns([1, 3, 1])   # square and centered — a stretched
            with mid:                            # radar distorts the comparison
                st.altair_chart(radar_chart(profiles, CATS, reference=REF),
                                use_container_width=False)
            st.caption("Radius = z-score clipped to [−1.5, +3]; the solid ring = league "
                       "average (z=0), the outer dashed one = z+3. TOV is already inverted "
                       "(further out = fewer turnovers). The gray dashed outline is the "
                       "Lobos: target spikes reaching past it = a hole he plugs.")
        else:
            st.info("Pick at least one player to draw the radar.")

# ---------- Draft raw list (seeds) ----------
with tab_draft:
    st.subheader("Draft — full raw list")
    st.caption("Every dimension of each prospect. Filter and sort however you like.")
    d2 = adv["draft2"].copy()
    DA = {"score": "Overall score", "pick_NBA": "NBA pick (earlier = better)",
          "curve_proj": "Projection", "opp_mult": "Opportunity", "min_vacuum": "Open slot on your team"}
    c1, c2, c3 = st.columns(3)
    poss = c1.multiselect("Position", sorted(d2["Pos"].dropna().unique()), default=[])
    so_pick = c2.checkbox("Only players with a 2026 NBA draft pick", value=False)
    ordd = c3.selectbox("Sort by", list(DA), format_func=lambda k: DA[k])
    dd = d2.copy()
    if poss:
        dd = dd[dd["Pos"].isin(poss)]
    if so_pick:
        dd = dd[dd["pick_NBA"].notna()]
    asc = ordd == "pick_NBA"
    st.caption(f"{len(dd)} prospects · sorted by **{DA[ordd]}**.")
    show(dd, cols=["Prospect", "Pos", "pick_NBA", "final_team", "curve_proj", "opp_mult",
                   "min_vacuum", "score"], sort=ordd, ascending=asc, bar="score", height=600)

# ---------- LEAGUE (seeds) ----------
with tab_liga:
    st.subheader("League strength by category")
    ls = cached_league_strength().sort_values("Total_VA", ascending=False)
    st.markdown("#### 🐺 Where the Lobos stand (rank per category, out of 24 teams)")
    st.caption("Smaller bar = better. A high rank = a category where you lose and need help.")
    my_ranks = {c: int(ls[c].rank(ascending=False, method="min")[ls["Franchise"] == MY_FRANCHISE].values[0])
                for c in CATS}
    st.bar_chart(pd.Series(my_ranks, name="Your rank (1=best)"), horizontal=True, color="#42a5f5")
    st.divider()
    st.markdown("#### Full table — 🟩 strong · 🟥 weak · **your team in blue**")
    lsr = ls.rename(columns={"Total_VA": "Total value"})
    sty = (lsr.style.map(lambda v: zcolor(v, scale=4), subset=CATS)
           .apply(highlight_mine, subset=["Franchise"]))
    st.dataframe(sty, width="stretch", hide_index=True, height=680)

# ---------- SALARIES (seeds) ----------
with tab_cap:
    st.subheader("League salaries (cap $190M)")
    cap = cached_team_cap()
    mine = cap[cap["Franchise"] == MY_FRANCHISE]
    if len(mine):
        m1, m2, m3 = st.columns(3)
        m1.metric("Your payroll (Year 1)", f"${mine['Payroll_M'].values[0]:.1f}M")
        m2.metric("Your free space", f"${mine['Space_M'].values[0]:.1f}M")
        m3.metric("Salary cap", "$190M")
    st.markdown("#### Payroll per team — who has spent the most")
    capsort = cap.sort_values("Payroll_M", ascending=False)
    st.bar_chart(capsort.set_index("Franchise")["Payroll_M"], horizontal=True, color="#ef5350")
    pos = list(capsort["Franchise"]).index(MY_FRANCHISE) + 1 if len(mine) else 0
    if pos:
        st.caption(f"🐺 The Lobos have the **#{pos} payroll** of 24 — "
                   f"{'heavily committed' if pos <= 6 else 'healthy space' if pos >= 14 else 'middle of the pack'}.")
    st.divider()
    st.markdown("#### 🐺 Your roster — who eats your cap")
    mr = cached_my_roster().copy()
    mr_paid = mr[mr["salary_y1_m"] > 0].sort_values("salary_y1_m", ascending=False)
    cA, cB = st.columns([1, 1])
    with cA:
        st.bar_chart(mr_paid.set_index("Player")["salary_y1_m"], horizontal=True, color="#ffa726")
    with cB:
        show(mr_paid, cols=["Player", "Pos", "salary_y1_m", "VA"], sort="salary_y1_m", height=340)
    st.divider()
    st.markdown("#### League table — each franchise's space")
    d = cap.sort_values("Space_M", ascending=False).rename(columns=NOMES)
    st.dataframe(
        d.style.map(lambda v: f"background-color:{'#1b5e20' if v > 20 else '#b71c1c' if v < 5 else ''}"
                    + (";color:white" if (v > 20 or v < 5) else ""), subset=["Cap space $M"])
        .apply(highlight_mine, subset=["Franchise"]),
        width="stretch", hide_index=True, height=420)

# ---------- NBA Averages & Metrics (dbt marts) ----------
PG = {"pts_pg": "PTS", "trb_pg": "REB", "ast_pg": "AST", "stocks_pg": "STOCKS",
      "three_p_pg": "3PM", "plus_minus_pg": "+/-", "tov_pg": "TOV"}
ZC = {"z_" + k.removesuffix("_pg"): v for k, v in PG.items()}  # same vocabulary as PG

with tab_nba1:
    seasons_df = q("select distinct season from analytics_marts.fct_player_fantasy_value_season order by season desc")
    if db_guard(seasons_df):
        seasons = seasons_df["season"].tolist()
        c0, c1 = st.columns([1, 1])
        season = c0.selectbox("NBA season", seasons, key="nba_season")
        min_g = c1.slider("Minimum games", 0, 82, 30, key="nba_ming")
        base = q(f"""
            select f.player_name, f.games_played as games, f.minutes_per_game as min,
                   f.pts_pg, f.trb_pg, f.ast_pg, f.stocks_pg, f.three_p_pg, f.plus_minus_pg, f.tov_pg,
                   a.per, a.ts_pct, a.usg_pct, a.win_shares, a.bpm, a.vorp
            from analytics_marts.fct_player_fantasy_value_season f
            left join analytics_marts.fct_player_advanced_stats a
              on a.player_name = f.player_name and a.season = f.season and a.season_type = 'regular'
            where f.season = '{season}'
        """)
        if db_guard(base):
            view = base[base["games"] >= min_g].copy()
            st.markdown("#### Per-game averages (standard)")
            std_cols = ["player_name", "games", "min"] + list(PG.keys())
            st.dataframe(view[std_cols].rename(columns=PG).sort_values("PTS", ascending=False),
                         width="stretch", hide_index=True, height=320)
            st.markdown("#### Advanced metrics (deeper)")
            advc = ["player_name", "per", "ts_pct", "usg_pct", "win_shares", "bpm", "vorp"]
            st.dataframe(
                view[advc].sort_values("win_shares", ascending=False, na_position="last"),
                width="stretch", hide_index=True, height=320,
                column_config={
                    "per": st.column_config.NumberColumn("PER", format="%.1f"),
                    "ts_pct": st.column_config.NumberColumn("TS%", format="%.3f"),
                    "usg_pct": st.column_config.NumberColumn("USG%", format="%.1f"),
                    "win_shares": st.column_config.NumberColumn("WS", format="%.1f"),
                    "bpm": st.column_config.NumberColumn("BPM", format="%.1f"),
                    "vorp": st.column_config.NumberColumn("VORP", format="%.1f"),
                })
            st.markdown("#### Player detail")
            who = st.selectbox("Player", sorted(view["player_name"]), key="nba_player")
            r = view[view["player_name"] == who].iloc[0]
            m = st.columns(7)
            for col, (k, lab) in zip(m, PG.items()):
                col.metric(lab, f"{r[k]:.1f}")
            a = st.columns(6)
            for col, (k, lab) in zip(a, [("per", "PER"), ("ts_pct", "TS%"), ("usg_pct", "USG%"),
                                         ("win_shares", "WS"), ("bpm", "BPM"), ("vorp", "VORP")]):
                col.metric(lab, "—" if pd.isna(r[k]) else f"{r[k]:.2f}")
            zrow = q(f"""select z_pts,z_trb,z_ast,z_stocks,z_three_p,z_plus_minus,z_tov
                         from analytics_marts.fct_player_fantasy_value_season
                         where player_name = '{who.replace("'", "''")}' and season = '{season}'""")
            if zrow is not None and not zrow.empty:
                prof = pd.DataFrame({"category": list(ZC.values()),
                                     "z-score": [zrow.iloc[0][k] for k in ZC]}).set_index("category")
                st.caption("Per-category profile (z>0 = above the league average)")
                st.bar_chart(prof, height=240)

# ---------- NBA Fantasy Value (dbt marts) ----------
with tab_nba2:
    st.caption("Value by z-score across the 7 categories (TOV inverted). The basis for draft/keepers/trades.")
    df = q("""
        select player_name, games_played, is_reference_pool,
               z_pts, z_trb, z_ast, z_stocks, z_three_p, z_plus_minus, z_tov
        from analytics_marts.fct_player_fantasy_value_season
    """)
    if db_guard(df):
        c1, c2, c3 = st.columns(3)
        only_pool = c1.checkbox("Reference pool only", value=True)
        min_games = c2.slider("Minimum games", 0, 82, 30, key="val_ming")
        punt = c3.multiselect("Punt (ignore categories)", list(ZC.values()))
        v = df.copy()
        if only_pool:
            v = v[v["is_reference_pool"]]
        v = v[v["games_played"] >= min_games]
        kept = [zc for zc, lab in ZC.items() if lab not in punt]
        v["value"] = v[kept].sum(axis=1).round(2)
        st.dataframe(
            v.sort_values("value", ascending=False)[
                ["player_name", "games_played", "value"] + list(ZC.keys())].head(60),
            width="stretch", hide_index=True,
            column_config={zc: st.column_config.NumberColumn(lab, format="%.2f")
                           for zc, lab in ZC.items()})
        with st.expander("🏅 Category leaders (top 5)"):
            cols = st.columns(len(ZC))
            for (zc, lab), col in zip(ZC.items(), cols):
                col.markdown(f"**{lab}**")
                for _, x in v.nlargest(5, zc)[["player_name", zc]].iterrows():
                    col.caption(f"{x['player_name']} ({x[zc]:.1f})")

# ---------- College (dbt marts) ----------
with tab_coll:
    cseasons_df = q("select distinct season from analytics_intermediate.int_prospect__college_stats order by season desc")
    if db_guard(cseasons_df):
        cs = st.selectbox("Season (college)", cseasons_df["season"].tolist(), key="coll_season")
        coll = q(f"""
            select player_name, school, class, archetype,
                   pts_per_40, trb_per_40, ast_per_40, stocks_per_40, three_p_per_40, tov_per_40,
                   ts_pct, usg_pct, team_sos
            from analytics_intermediate.int_prospect__college_stats
            where season = '{cs}' order by pts_per_40 desc
        """)
        if db_guard(coll):
            st.markdown(f"#### Prospects in {cs} — per-40-min averages")
            st.dataframe(coll, width="stretch", hide_index=True, height=320)
            st.markdown("#### A prospect's development (multi-season)")
            multi = q("""
                select cbb_id, player_name from analytics_intermediate.int_prospect__college_stats
                group by cbb_id, player_name having count(*) >= 2 order by player_name
            """)
            if db_guard(multi):
                lbl = dict(zip(multi["player_name"] + " (" + multi["cbb_id"] + ")", multi["cbb_id"]))
                pick = st.selectbox("Prospect", list(lbl.keys()), key="coll_evo")
                traj = q(f"""
                    select season, pts_per_40, trb_per_40, ast_per_40, stocks_per_40, three_p_per_40
                    from analytics_intermediate.int_prospect__college_stats
                    where cbb_id = '{lbl[pick]}' order by season
                """)
                if db_guard(traj):
                    traj = traj.set_index("season")
                    traj.columns = ["PTS/40", "REB/40", "AST/40", "STK/40", "3PM/40"]
                    st.line_chart(traj, height=300)

# ---------- Draft scouting (dbt marts) ----------
with tab_scout:
    st.caption("NBA projection = average outcome of the historical comps + a confidence signal (D-33).")
    df = q("""
        select prospect_name, prospect_season, prospect_archetype, confidence,
               n_comps_with_outcome, n_comps_with_6cat, mean_comp_distance,
               proj_pg_pts, proj_pg_trb, proj_pg_ast, proj_pg_stocks, proj_pg_fg3, proj_pg_tov,
               proj_win_shares, proj_vorp
        from analytics_marts.fct_prospect_scouting
    """)
    if db_guard(df):
        c1, c2 = st.columns(2)
        # confidence values come from the mart in Portuguese (alta/media/baixa) —
        # keep the raw values for filtering and translate only the display
        CONF_LABELS = {"alta": "high", "media": "medium", "baixa": "low"}
        confs = c1.multiselect("Confidence", ["alta", "media", "baixa"],
                               default=["alta", "media", "baixa"],
                               format_func=lambda v: CONF_LABELS.get(v, v))
        archs = c2.multiselect("Archetype", sorted(df["prospect_archetype"].dropna().unique()),
                               default=sorted(df["prospect_archetype"].dropna().unique()))
        view = df[df["confidence"].isin(confs) & df["prospect_archetype"].isin(archs)]
        st.dataframe(view.sort_values("proj_win_shares", ascending=False, na_position="last"),
                     width="stretch", hide_index=True)

# ---------- Comps (dbt marts) ----------
with tab_comps:
    prospects = q("select distinct prospect_id, prospect_name from analytics_intermediate.int_prospect__comps order by prospect_name")
    if db_guard(prospects):
        label_to_id = dict(zip(prospects["prospect_name"], prospects["prospect_id"]))
        pickc = st.selectbox("Prospect", list(label_to_id.keys()), key="comp_pick")
        comps = q(f"""
            with o as (select cbb_id from analytics_marts.fct_college_to_nba_outcomes)
            select c.comp_rank, c.comp_name, c.comp_season, c.comp_archetype,
                   c.distance, c.used_archetype_fallback, (o.cbb_id is not null) as reached_nba
            from analytics_intermediate.int_prospect__comps c
            left join o on o.cbb_id = c.comp_id
            where c.prospect_id = '{label_to_id[pickc]}' order by c.comp_rank
        """)
        if db_guard(comps):
            st.dataframe(comps, width="stretch", hide_index=True)

# ---------- News (RSS; pool players via DB with a seed fallback) ----------
with tab_news:
    st.caption("Sources: ESPN, Yahoo, CBS (free RSS). No Twitter/Shams (paid API).")

    @st.cache_data(ttl=900)
    def _news():
        return get_nba_news()

    news = _news()
    if news.empty:
        st.warning("Couldn't fetch the news right now.")
    else:
        pool_df = q("select distinct player_name from analytics_marts.fct_player_fantasy_value_season where is_reference_pool")
        if pool_df is not None and not pool_df.empty:
            players = pool_df["player_name"].dropna().tolist()
        else:   # DB-less fallback: rotation pool from the seeds (tolerant _f parse —
            # BBR may let a repeated header row slip through; astype would break)
            players = eng.reference_pool()["Player"].dropna().tolist()
        news = tag_players(news.copy(), players)
        c1, c2 = st.columns([2, 1])
        termo = c1.text_input("Search", "")
        so_pool = c2.checkbox("Only mentioning pool players", value=False)
        vw = news
        if so_pool:
            vw = vw[vw["players"] != ""]
        if termo:
            vw = vw[(vw["title"] + " " + vw["summary"]).str.contains(termo, case=False, na=False)]
        st.caption(f"{len(vw)} headlines")
        for _, r in vw.iterrows():
            tag = f" · **{r['players']}**" if r["players"] else ""
            st.markdown(f"**[{r['title']}]({r['link']})**  \n*{r['source']} · {r['published']}*{tag}")
            st.divider()
