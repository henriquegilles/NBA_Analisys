"""
Painel da camada Fantasy (Bandeja de 3) — Streamlit.

Lê os marts dbt direto do Postgres (mesmos env vars do dbt). Três visões:
  1. Minha Franquia — valoração por z-score (Domínio A).
  2. Scouting de Draft — projeção + sinal de confiança (Domínio B).
  3. Explorador de Comps — os k vizinhos de um prospecto e quem chegou à NBA.

Rodar:
    source .venv/bin/activate
    docker compose up -d postgres        # banco de pé (runbook #23)
    streamlit run dashboard/app.py
"""

import os
import pandas as pd
import psycopg2
import streamlit as st

from news import get_nba_news, tag_players

st.set_page_config(page_title="Bandeja de 3 — Painel", layout="wide")


@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DBT_HOST", "localhost"),
        port=os.getenv("DBT_PORT", "5432"),
        dbname=os.getenv("DBT_DBNAME", "nba"),
        user=os.getenv("DBT_USER", "postgres"),
        password=os.getenv("DBT_PASSWORD", "postgres"),
    )


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_conn())


st.title("🏀 Bandeja de 3 — Painel de Análise")

tab_a, tab_b, tab_comps, tab_news = st.tabs(
    ["Minha Franquia (valoração)", "Scouting de Draft", "Explorador de Comps", "Notícias NBA"]
)

# ── Domínio A — valoração por z-score ───────────────────────────────────────
with tab_a:
    st.subheader("Valoração de jogadores — temporada (z-score por categoria)")
    st.caption("z_total = soma dos 7 z-scores da liga (default oficial, D-22). Maior = mais valioso.")
    df = q("""
        select player_name, season, games_played, minutes_per_game,
               is_reference_pool, z_total, z_mean
        from analytics_marts.fct_player_fantasy_value_season
        order by z_total desc nulls last
    """)
    col1, col2 = st.columns(2)
    only_pool = col1.checkbox("Só pool de referência", value=True)
    top_n = col2.slider("Top N", 10, 200, 30, step=10)
    view = df[df["is_reference_pool"]] if only_pool else df
    st.dataframe(view.head(top_n), use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} jogadores no total.")

# ── Domínio B — scouting de draft ───────────────────────────────────────────
with tab_b:
    st.subheader("Projeção de prospectos (média dos comps) + confiança")
    st.caption(
        "Projeção NBA = desfecho médio dos comps históricos. `confidence` combina "
        "cobertura 6-cat, fallback de arquétipo e distância (D-33)."
    )
    df = q("""
        select prospect_name, prospect_season, prospect_archetype, confidence,
               n_comps_with_outcome, n_comps_with_6cat, mean_comp_distance,
               proj_pg_pts, proj_pg_trb, proj_pg_ast,
               proj_pg_stocks, proj_pg_fg3, proj_pg_tov,
               proj_win_shares, proj_vorp
        from analytics_marts.fct_prospect_scouting
    """)
    c1, c2, c3 = st.columns(3)
    confs = c1.multiselect("Confiança", ["alta", "media", "baixa"], default=["alta", "media", "baixa"])
    archs = c2.multiselect("Arquétipo", sorted(df["prospect_archetype"].dropna().unique()),
                           default=sorted(df["prospect_archetype"].dropna().unique()))
    sort_by = c3.selectbox("Ordenar por", ["proj_win_shares", "proj_pg_pts", "proj_vorp", "mean_comp_distance"])
    view = df[df["confidence"].isin(confs) & df["prospect_archetype"].isin(archs)]
    view = view.sort_values(sort_by, ascending=False, na_position="last")
    st.dataframe(view, use_container_width=True, hide_index=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Prospectos", len(view))
    m2.metric("Confiança alta", int((view["confidence"] == "alta").sum()))
    m3.metric("Distância média", round(view["mean_comp_distance"].mean(), 2) if len(view) else 0)

# ── Explorador de comps ─────────────────────────────────────────────────────
with tab_comps:
    st.subheader("Os k comps de um prospecto")
    prospects = q("""
        select distinct prospect_id, prospect_name
        from analytics_intermediate.int_prospect__comps
        order by prospect_name
    """)
    label_to_id = dict(zip(prospects["prospect_name"], prospects["prospect_id"]))
    pick = st.selectbox("Prospecto", list(label_to_id.keys()))
    pid = label_to_id[pick]
    comps = q(f"""
        with o as (select cbb_id from analytics_marts.fct_college_to_nba_outcomes)
        select c.comp_rank, c.comp_name, c.comp_season, c.comp_archetype,
               c.distance, c.used_archetype_fallback,
               (o.cbb_id is not null) as chegou_nba
        from analytics_intermediate.int_prospect__comps c
        left join o on o.cbb_id = c.comp_id
        where c.prospect_id = '{pid}'
        order by c.comp_rank
    """)
    st.dataframe(comps, use_container_width=True, hide_index=True)
    st.caption("`chegou_nba` = esse comp tem desfecho NBA e entra na média da projeção.")

# ── Notícias NBA (RSS grátis) ───────────────────────────────────────────────
with tab_news:
    st.subheader("Últimas da NBA — contexto pra decisões (RSS grátis)")
    st.caption("Fontes: ESPN, Yahoo, CBS. Sem Twitter/Shams (exigiria API paga do X).")

    @st.cache_data(ttl=900)
    def _news():
        return get_nba_news()

    news = _news()
    if news.empty:
        st.warning("Não consegui buscar as notícias agora (rede/feed indisponível).")
    else:
        players = q("""
            select distinct player_name
            from analytics_marts.fct_player_fantasy_value_season
            where is_reference_pool
        """)["player_name"].dropna().tolist()
        news = tag_players(news.copy(), players)

        c1, c2 = st.columns([2, 1])
        termo = c1.text_input("Buscar (jogador, time, palavra-chave)", "")
        so_pool = c2.checkbox("Só citando jogadores do pool", value=False)

        view = news
        if so_pool:
            view = view[view["jogadores"] != ""]
        if termo:
            mask = (view["titulo"] + " " + view["resumo"]).str.contains(termo, case=False, na=False)
            view = view[mask]

        st.caption(f"{len(view)} manchetes")
        for _, r in view.iterrows():
            tag = f" · **{r['jogadores']}**" if r["jogadores"] else ""
            st.markdown(f"**[{r['titulo']}]({r['link']})**  \n*{r['fonte']} · {r['publicado']}*{tag}")
            if r["resumo"]:
                st.caption(r["resumo"])
            st.divider()
