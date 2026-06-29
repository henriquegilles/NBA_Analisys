"""
Painel da camada Fantasy (Bandeja de 3) — Streamlit.

Lê os marts dbt direto do Postgres (mesmos env vars do dbt). Abas:
  1. NBA — Médias & Métricas : médias por-jogo padrão + métricas avançadas + detalhe visual.
  2. NBA — Valor Fantasy     : valoração por z-score, construtor de punt, líderes.
  3. Calouros (College)      : stats por temporada + gráfico de evolução do prospecto.
  4. Scouting de Draft       : projeção + sinal de confiança.
  5. Comps                   : os k vizinhos de um prospecto.
  6. Notícias NBA            : RSS grátis, com tag de jogadores do pool.

Rodar:  streamlit run dashboard/app.py   →  http://localhost:8501
"""

import os
import sys
import pandas as pd
import psycopg2
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news import get_nba_news, tag_players

st.set_page_config(page_title="Bandeja de 3 — Painel", layout="wide")


@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DBT_HOST", "localhost"), port=os.getenv("DBT_PORT", "5432"),
        dbname=os.getenv("DBT_DBNAME", "nba"), user=os.getenv("DBT_USER", "postgres"),
        password=os.getenv("DBT_PASSWORD", "postgres"),
    )


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_conn())


st.title("🏀 Bandeja de 3 — Painel de Análise")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "NBA — Médias & Métricas", "NBA — Valor Fantasy", "Calouros (College)",
    "Scouting de Draft", "Comps", "Notícias NBA",
])

# Rótulos amigáveis das categorias
PG = {"pts_pg": "PTS", "trb_pg": "REB", "ast_pg": "AST", "stocks_pg": "STOCKS",
      "three_p_pg": "3PM", "plus_minus_pg": "+/-", "tov_pg": "TOV"}
ZC = {"z_pts": "PTS", "z_trb": "REB", "z_ast": "AST", "z_stocks": "STOCKS",
      "z_three_p": "3PM", "z_plus_minus": "+/-", "z_tov": "TOV"}

# ── 1. NBA — Médias & Métricas (padrão + profundas) ─────────────────────────
with tab1:
    seasons = q("select distinct season from analytics_marts.fct_player_fantasy_value_season order by season desc")["season"].tolist()
    c0, c1 = st.columns([1, 1])
    season = c0.selectbox("Temporada NBA", seasons, key="nba_season")
    min_g = c1.slider("Mínimo de jogos", 0, 82, 30, key="nba_ming")

    base = q(f"""
        select f.player_name, f.games_played as jogos, f.minutes_per_game as min,
               f.pts_pg, f.trb_pg, f.ast_pg, f.stocks_pg, f.three_p_pg, f.plus_minus_pg, f.tov_pg,
               a.per, a.ts_pct, a.usg_pct, a.win_shares, a.bpm, a.vorp
        from analytics_marts.fct_player_fantasy_value_season f
        left join analytics_marts.fct_player_advanced_stats a
          on a.player_name = f.player_name and a.season = f.season and a.season_type = 'regular'
        where f.season = '{season}'
    """)
    view = base[base["jogos"] >= min_g].copy()

    st.markdown("#### Médias por-jogo (padrão)")
    std_cols = ["player_name", "jogos", "min"] + list(PG.keys())
    st.dataframe(
        view[std_cols].rename(columns=PG).sort_values("PTS", ascending=False),
        use_container_width=True, hide_index=True, height=320,
    )

    st.markdown("#### Métricas avançadas (mais profundas)")
    adv = ["player_name", "per", "ts_pct", "usg_pct", "win_shares", "bpm", "vorp"]
    st.dataframe(
        view[adv].sort_values("win_shares", ascending=False, na_position="last"),
        use_container_width=True, hide_index=True, height=320,
        column_config={
            "per": st.column_config.NumberColumn("PER", format="%.1f"),
            "ts_pct": st.column_config.NumberColumn("TS%", format="%.3f"),
            "usg_pct": st.column_config.NumberColumn("USG%", format="%.1f"),
            "win_shares": st.column_config.NumberColumn("WS", format="%.1f"),
            "bpm": st.column_config.NumberColumn("BPM", format="%.1f"),
            "vorp": st.column_config.NumberColumn("VORP", format="%.1f"),
        },
    )

    st.markdown("#### Detalhe do jogador")
    who = st.selectbox("Jogador", sorted(view["player_name"]), key="nba_player")
    r = view[view["player_name"] == who].iloc[0]
    m = st.columns(7)
    for col, (k, lab) in zip(m, PG.items()):
        col.metric(lab, f"{r[k]:.1f}")
    a = st.columns(6)
    for col, (k, lab) in zip(a, [("per", "PER"), ("ts_pct", "TS%"), ("usg_pct", "USG%"),
                                 ("win_shares", "WS"), ("bpm", "BPM"), ("vorp", "VORP")]):
        col.metric(lab, "—" if pd.isna(r[k]) else f"{r[k]:.2f}")
    # Perfil de categoria (z-score) — barra visual de forças/fraquezas
    zrow = q(f"""select z_pts,z_trb,z_ast,z_stocks,z_three_p,z_plus_minus,z_tov
                 from analytics_marts.fct_player_fantasy_value_season
                 where player_name = '{who.replace("'", "''")}' and season = '{season}'""")
    if not zrow.empty:
        prof = pd.DataFrame({"categoria": list(ZC.values()),
                             "z-score": [zrow.iloc[0][k] for k in ZC]}).set_index("categoria")
        st.caption("Perfil por categoria (z>0 = acima da média da liga)")
        st.bar_chart(prof, height=240)

# ── 2. NBA — Valor Fantasy (z-score + punt) ─────────────────────────────────
with tab2:
    st.caption("Valor por z-score nas 7 categorias (TOV invertido: z maior = melhor). Base pra draft/keepers/trocas.")
    df = q("""
        select player_name, games_played, is_reference_pool,
               z_pts, z_trb, z_ast, z_stocks, z_three_p, z_plus_minus, z_tov
        from analytics_marts.fct_player_fantasy_value_season
    """)
    c1, c2, c3 = st.columns(3)
    only_pool = c1.checkbox("Só pool de referência", value=True)
    min_games = c2.slider("Mínimo de jogos", 0, 82, 30, key="val_ming")
    punt = c3.multiselect("Punt (ignorar categorias)", list(ZC.values()))
    v = df.copy()
    if only_pool:
        v = v[v["is_reference_pool"]]
    v = v[v["games_played"] >= min_games]
    kept = [zc for zc, lab in ZC.items() if lab not in punt]
    v["valor"] = v[kept].sum(axis=1).round(2)
    st.dataframe(
        v.sort_values("valor", ascending=False)[["player_name", "games_played", "valor"] + list(ZC.keys())].head(60),
        use_container_width=True, hide_index=True,
        column_config={zc: st.column_config.NumberColumn(lab, format="%.2f") for zc, lab in ZC.items()},
    )
    with st.expander("🏅 Líderes por categoria (top 5)"):
        cols = st.columns(len(ZC))
        for (zc, lab), col in zip(ZC.items(), cols):
            col.markdown(f"**{lab}**")
            for _, x in v.nlargest(5, zc)[["player_name", zc]].iterrows():
                col.caption(f"{x['player_name']} ({x[zc]:.1f})")

# ── 3. Calouros (College) — por temporada + evolução ────────────────────────
with tab3:
    cseasons = q("select distinct season from analytics_intermediate.int_prospect__college_stats order by season desc")["season"].tolist()
    cs = st.selectbox("Temporada (college)", cseasons, key="coll_season")
    coll = q(f"""
        select player_name, school, class, archetype,
               pts_per_40, trb_per_40, ast_per_40, stocks_per_40, three_p_per_40, tov_per_40,
               ts_pct, usg_pct, team_sos
        from analytics_intermediate.int_prospect__college_stats
        where season = '{cs}'
        order by pts_per_40 desc
    """)
    st.markdown(f"#### Prospectos em {cs} — médias por-40-min")
    st.dataframe(coll, use_container_width=True, hide_index=True, height=320)

    st.markdown("#### Evolução de um prospecto (multi-temporada)")
    multi = q("""
        select cbb_id, player_name from analytics_intermediate.int_prospect__college_stats
        group by cbb_id, player_name having count(*) >= 2 order by player_name
    """)
    lbl = dict(zip(multi["player_name"] + " (" + multi["cbb_id"] + ")", multi["cbb_id"]))
    pick = st.selectbox("Prospecto", list(lbl.keys()), key="coll_evo")
    traj = q(f"""
        select season, pts_per_40, trb_per_40, ast_per_40, stocks_per_40, three_p_per_40
        from analytics_intermediate.int_prospect__college_stats
        where cbb_id = '{lbl[pick]}' order by season
    """).set_index("season")
    traj.columns = ["PTS/40", "REB/40", "AST/40", "STK/40", "3PM/40"]
    st.line_chart(traj, height=300)

# ── 4. Scouting de Draft ────────────────────────────────────────────────────
with tab4:
    st.caption("Projeção NBA = desfecho médio dos comps históricos + sinal de confiança (D-33).")
    df = q("""
        select prospect_name, prospect_season, prospect_archetype, confidence,
               n_comps_with_outcome, n_comps_with_6cat, mean_comp_distance,
               proj_pg_pts, proj_pg_trb, proj_pg_ast, proj_pg_stocks, proj_pg_fg3, proj_pg_tov,
               proj_win_shares, proj_vorp
        from analytics_marts.fct_prospect_scouting
    """)
    c1, c2 = st.columns(2)
    confs = c1.multiselect("Confiança", ["alta", "media", "baixa"], default=["alta", "media", "baixa"])
    archs = c2.multiselect("Arquétipo", sorted(df["prospect_archetype"].dropna().unique()),
                           default=sorted(df["prospect_archetype"].dropna().unique()))
    view = df[df["confidence"].isin(confs) & df["prospect_archetype"].isin(archs)]
    st.dataframe(view.sort_values("proj_win_shares", ascending=False, na_position="last"),
                 use_container_width=True, hide_index=True)

# ── 5. Comps ────────────────────────────────────────────────────────────────
with tab5:
    prospects = q("select distinct prospect_id, prospect_name from analytics_intermediate.int_prospect__comps order by prospect_name")
    label_to_id = dict(zip(prospects["prospect_name"], prospects["prospect_id"]))
    pickc = st.selectbox("Prospecto", list(label_to_id.keys()), key="comp_pick")
    comps = q(f"""
        with o as (select cbb_id from analytics_marts.fct_college_to_nba_outcomes)
        select c.comp_rank, c.comp_name, c.comp_season, c.comp_archetype,
               c.distance, c.used_archetype_fallback, (o.cbb_id is not null) as chegou_nba
        from analytics_intermediate.int_prospect__comps c
        left join o on o.cbb_id = c.comp_id
        where c.prospect_id = '{label_to_id[pickc]}' order by c.comp_rank
    """)
    st.dataframe(comps, use_container_width=True, hide_index=True)

# ── 6. Notícias NBA ─────────────────────────────────────────────────────────
with tab6:
    st.caption("Fontes: ESPN, Yahoo, CBS (RSS grátis). Sem Twitter/Shams (exigiria API paga do X).")

    @st.cache_data(ttl=900)
    def _news():
        return get_nba_news()

    news = _news()
    if news.empty:
        st.warning("Não consegui buscar as notícias agora.")
    else:
        players = q("select distinct player_name from analytics_marts.fct_player_fantasy_value_season where is_reference_pool")["player_name"].dropna().tolist()
        news = tag_players(news.copy(), players)
        c1, c2 = st.columns([2, 1])
        termo = c1.text_input("Buscar", "")
        so_pool = c2.checkbox("Só citando jogadores do pool", value=False)
        vw = news
        if so_pool:
            vw = vw[vw["jogadores"] != ""]
        if termo:
            vw = vw[(vw["titulo"] + " " + vw["resumo"]).str.contains(termo, case=False, na=False)]
        st.caption(f"{len(vw)} manchetes")
        for _, r in vw.iterrows():
            tag = f" · **{r['jogadores']}**" if r["jogadores"] else ""
            st.markdown(f"**[{r['titulo']}]({r['link']})**  \n*{r['fonte']} · {r['publicado']}*{tag}")
            st.divider()
