"""
Painel unificado da Bandeja de 3 — Streamlit (fusão de app.py + fantasy_gm_tool.py,
Rodada 6 Fase 2). UM entrypoint:

    streamlit run dashboard/app.py    →  http://localhost:8501

Duas famílias de abas:
  - SEEDS (sempre funcionam, sem banco): Meu Time, Predicts, Guerra, FA, Draft,
    Liga, Salários — motor `fantasy_engine`/`fa_draft_engine`/`predicts`.
  - MARTS dbt (precisam do Postgres): NBA Médias, NBA Valor, College, Scouting,
    Comps — sem banco mostram aviso claro (nunca stacktrace).

Smoke-test headless de todas as abas: python dashboard/test_app_smoke.py
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

st.title("🏀 Bandeja de 3 — Central do GM do Lobos")
st.caption("Como ler os números: **Valor / Nota** — quanto maior, melhor. "
           "**Categorias coloridas** — 🟩 verde = forte · 🟥 vermelho = fraco.")

(tab_time, tab_players, tab_pred, tab_war, tab_fa2, tab_draft2, tab_fa, tab_draft,
 tab_liga, tab_cap, tab_nba1, tab_nba2, tab_coll, tab_scout, tab_comps,
 tab_news) = st.tabs([
    "🧢 Meu time", "👥 Players", "🔮 Predicts", "⚔️ Guerra", "🎯 Free Agency",
    "🏆 Draft", "🔎 FA (lista crua)", "🔎 Draft (lista crua)", "🏅 Liga",
    "💰 Salários", "📊 NBA Médias", "💎 NBA Valor", "🎓 College", "🔭 Scouting",
    "🧬 Comps", "📰 Notícias",
])

# ---------- MEU TIME (seeds) ----------
with tab_time:
    st.subheader(f"Elenco do {MY_FRANCHISE}")
    mr = cached_my_roster()
    try:
        fc = pd.read_csv(os.path.join(eng.seeds, "fantasy_contracts.csv"))
        roster_names = set(pd.read_csv(os.path.join(eng.seeds, "my_roster.csv"))
                           ["player_name"].str.lower())
        fc = fc[fc["player_name"].str.lower().isin(roster_names)]  # contrato órfão
        caps = st.columns(3)                                       # não conta no cap
        for col, yr, lab in zip(caps, ["salary_y1", "salary_y2", "salary_y3"],
                                ["Ano 1", "Ano 2", "Ano 3"]):
            col.metric(f"Cap {lab}", f"${fc[yr].fillna(0).sum()/1e6:.1f}M")
    except Exception as e:      # seed ausente/corrompido não derruba a aba
        st.caption(f"(contratos indisponíveis: {e})")
    prof = pd.DataFrame({
        "Categoria": [CAT_LABELS[c] for c in CATS],
        "Força do time": [round(mr[f"z_{c}"].dropna().nlargest(10).mean(), 2) for c in CATS],
    }).sort_values("Força do time")
    st.markdown("#### Onde o time é forte e fraco")
    st.caption("Barra pra **direita** = você ganha essa categoria da liga. Pra **esquerda** = "
               "precisa reforçar. (0 = na média da liga.)")
    st.bar_chart(prof.set_index("Categoria"), horizontal=True, color="#42a5f5")
    fraca = prof.iloc[0]["Categoria"]
    st.info(f"🎯 Seu maior buraco hoje: **{fraca}** — priorize em FA e no draft.")
    st.markdown("#### Elenco (verde = manda bem na categoria · vermelho = fraco)")
    show(mr, cols=["Jogador", "Pos", "Age", "salary_y1_m", "VA",
                   "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV"],
         sort="VA", color_z=True, bar="VA", height=680)
    rookies = mr[mr["VA"].isna()]["Jogador"].tolist()
    if rookies:
        st.markdown("#### Calouros / sem stats NBA → ver aba **🔭 Scouting**")
        st.write(", ".join(rookies))
    with st.expander("Visão 7-cat com +/- e jogos (mart dbt fct_my_roster)"):
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
    st.subheader("👥 Players da liga — todos os jogadores rosterados")
    st.caption("Mesmo mapa de calor do **Meu time**, para as 24 franquias: "
               "🟩 verde = forte na categoria · 🟥 vermelho = fraco. "
               "Jogadores sem valoração (calouros/sem stats NBA) ficam sem cor.")
    lp = cached_league_players()
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    franquias = fc1.multiselect("Franquia", sorted(lp["Franquia"].unique()),
                                placeholder="Todas as franquias")
    posicoes = ["Todas"] + sorted(lp["Pos"].dropna().unique().tolist())
    pos = fc2.selectbox("Posição", posicoes, key="players_pos")
    busca = fc3.text_input("Buscar jogador", key="players_busca")
    filt = lp
    if franquias:
        filt = filt[filt["Franquia"].isin(franquias)]
    if pos != "Todas":
        filt = filt[filt["Pos"] == pos]
    if busca.strip():
        filt = filt[filt["Jogador"].str.contains(busca.strip(), case=False, na=False)]
    st.caption(f"{len(filt)} jogadores · {filt['Franquia'].nunique()} franquias")
    show(filt, cols=["Jogador", "Franquia", "Pos", "Age", "salary_y1_m", "VA",
                     "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV"],
         sort="VA", color_z=True, bar="VA", height=680)

# ---------- PREDICTS (seeds; Fase 1) ----------
with tab_pred:
    st.subheader("🔮 Predicts v2 — projeção 2026-27 do elenco")
    st.caption("VA projetado = minutos ajustados pelo papel 2026-27 (fonte por linha no seed "
               "`nba_context_overrides`) × curva de idade. **⚠️ G<25 = amostra ruidosa.** "
               "Floor/Ceiling = percentis 20/85 do score por jogo; CV = risco (volatilidade).")
    p = load_predicts()
    pred = cached_roster_predicts()
    c1, c2, c3 = st.columns(3)
    ok = pred["VA_proj_2627"].dropna()
    c1.metric("VA projetado do elenco (soma)", f"{ok.sum():.1f}")
    c2.metric("Melhor projeção", f"{pred.iloc[0]['Jogador']} ({pred.iloc[0]['VA_proj_2627']})")
    ruido = int((pred["flag_amostra"].astype(str).str.len() > 0).sum())
    c3.metric("Jogadores com amostra ruidosa", ruido)
    st.markdown("#### Tabela consolidada (ordenada pela projeção 2026-27)")
    st.dataframe(pred, width="stretch", hide_index=True, height=620)
    cA, cB = st.columns(2)
    with cA:
        st.markdown("#### Sensibilidade a minutos (@24 → @32)")
        sens = pred.dropna(subset=["VA@24"]).set_index("Jogador")[["VA@24", "VA@28", "VA@32"]]
        st.dataframe(sens.style.map(zcolor), width="stretch", height=400)
    with cB:
        st.markdown("#### Curva de idade usada")
        st.caption("Paramétrica (pico 26-28, declínio >30) — ver doc 09 §15.3.")
        st.line_chart(p.aging_curve(), height=300)
        with st.expander("Casos de validação direcional (Butler/Vučević/Claxton/Ware)"):
            st.dataframe(p.validation_cases(), hide_index=True)

# ---------- GUERRA (seeds) ----------
with tab_war:
    st.subheader("⚔️ Guerra — você contra qualquer rival, categoria a categoria")
    mat = cached_team_cat_matrix()
    rivals = [f for f in mat.index if f != MY_FRANCHISE]
    rival = st.selectbox("Rival", rivals)
    me, rv = mat.loc[MY_FRANCHISE], mat.loc[rival]
    diff = (me - rv).round(1)
    wins = int(sum(diff[c] > 0 for c in CATS))
    c1, c2, c3 = st.columns(3)
    c1.metric("Categorias que você vence", f"{wins} de {len(CATS)}")
    c2.metric("Resultado do confronto",   # 7 cats: 4+ leva, não existe empate
              "✅ VITÓRIA" if wins >= 4 else "❌ DERROTA")
    closest = diff.abs().idxmin()
    c3.metric("Categoria mais apertada", f"{CAT_LABELS.get(closest, closest)} ({diff[closest]:+.1f}z)")
    st.caption("Margem = diferença na soma de z-scores do top-10 de cada elenco. "
               "|margem| < 2z ≈ vira com uma semana boa/ruim — é onde mora a variância. "
               "TOV entra na conta do confronto (regra da liga), mesmo com nosso build punt-TOV. "
               "Margem 0,0 = empate NA categoria — regra de desempate da liga desconhecida; "
               "aqui conta como não-vitória (leitura conservadora).")
    comp = pd.DataFrame({"Você": me[CATS].values, rival: rv[CATS].values,
                         "Margem": diff[CATS].values},
                        index=[CAT_LABELS[c] for c in CATS])
    st.markdown("#### Margem por categoria (positivo = você vence)")
    st.bar_chart(comp["Margem"], horizontal=True, color="#ef5350")
    st.dataframe(comp.style.map(zcolor, subset=["Margem"]), width="stretch")
    perigo = [CAT_LABELS[c] for c in CATS if 0 < diff[c] <= 2]
    if perigo:
        st.warning(f"🔥 Vitórias por um fio (≤2z): **{', '.join(perigo)}** — blindar essas "
                   "categorias é o que segura o confronto contra variância semanal.")

# ---------- FREE AGENCY 2.0 (seeds) ----------
with tab_fa2:
    st.subheader("🎯 Melhores alvos de Free Agency")
    st.markdown("#### Quanto cada categoria vale PRA VOCÊ vencer")
    st.caption("Barra maior = ganhar nessa categoria te dá mais vitórias. É o que o ranking prioriza.")
    w = adv["weights"].copy()
    w["Ganho de vitória"] = (w["peso_dwinrate"] * 100).round(1)
    w["Categoria"] = w["categoria"]
    st.bar_chart(w.set_index("Categoria")["Ganho de vitória"], horizontal=True, color="#66bb6a")
    top_lever = w.sort_values("peso_dwinrate", ascending=False).iloc[0]
    c1, c2 = st.columns(2)
    c1.metric("Chance de vencer um confronto hoje", f"{adv['base_wr']*100:.0f}%")
    c2.metric("Categoria que mais te faz vencer", top_lever["categoria"],
              f"+{top_lever['peso_dwinrate']*100:.0f}pp por reforço")
    st.divider()
    st.markdown("#### Ranking de alvos (livres na liga, ponderado pelo que você precisa)")
    st.caption("**Nota** = valor do jogador + encaixe no que falta − risco de lesão. "
               "**Saúde** = 100% sem lesão.")
    show(adv["fa_board"], cols=["Jogador", "Pos", "Age", "score", "VA", "va_over_repl",
                                "injury_disc", "ctx_mult"],
         sort="score", bar="score", pct=["injury_disc", "ctx_mult"], height=560)
    with st.expander("⚔️ Quem mais briga pelos MESMOS alvos que você (rivais)"):
        show(adv["rivals"], cols=["Franquia", "cap_livre_M", "categorias_fracas", "ameaca_FA"],
             sort="cap_livre_M")
    with st.expander("🔔 Times lotados que vão CORTAR bons jogadores (waiver)"):
        show(adv["waiver"], cols=["Franquia", "corte_provavel", "VA"], sort="VA")

# ---------- DRAFT 2.0 (seeds) ----------
with tab_draft2:
    st.subheader("🏆 Board de Draft 2026 (talento × oportunidade)")
    st.caption("**Nota** junta: posição no draft NBA + time que dá minutos (rebuild) + vaga no seu elenco.")
    d2 = adv["draft2"].copy()
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        st.markdown("#### Top 15 prospectos (por Nota)")
        top15 = d2.sort_values("score", ascending=False).head(15)
        st.bar_chart(top15.set_index("Prospecto")["score"], horizontal=True, color="#ab47bc")
    with cc2:
        st.markdown("#### Valor × posição no draft")
        st.caption("Alto num pick tardio = **sleeper**; baixo num pick alto = risco.")
        sc = d2[d2["pick_NBA"].notna()].rename(columns={"pick_NBA": "Pick NBA", "score": "Nota"})
        st.scatter_chart(sc, x="Pick NBA", y="Nota", color="#ab47bc", height=340)
    st.markdown("#### Board completo")
    show(d2, cols=["Prospecto", "Pos", "pick_NBA", "time_final", "score", "proj_curva",
                   "opp_mult", "vacuo_min"], sort="score", bar="score", height=380)
    st.divider()
    st.markdown("#### Vale a pena COMPRAR uma pick numa troca?")
    st.caption("Produção esperada da pick × preço real (em jogadores) nas trades da liga.")
    buy = adv["buy"].rename(columns={
        "pick": "Pick nº", "rodada": "Rodada", "prod_esperada": "Produção esperada",
        "custo_pick_M": "Custo em jogadores $M", "salario_rookie_M": "Salário rookie $M",
        "vale_comprar": "Vale comprar?"})
    st.dataframe(
        buy.style.map(lambda v: "background-color:#1b5e20;color:white" if v == "SIM"
                      else "background-color:#5d4037" if v == "só se barato" else "",
                      subset=["Vale comprar?"]),
        width="stretch", hide_index=True)
    st.info("💡 Regra rápida: pick de 1ª custa ~**$34M** em jogadores — só vale nas **~15 "
            "primeiras**. Pick tardia de 1ª: só se baratear. Pick de 2ª (~$14M) rende bem.")

# ---------- FA lista crua (seeds) ----------
with tab_fa:
    st.subheader("Free Agency — lista crua (todos os aspectos)")
    st.caption("**Dono atual** = franquia que segura o passe (pode cobrir a oferta se estiver "
               "no playoff); '(livre)' = sem dono.")
    fa = cached_fa_targets(120)
    ASPECTOS = {"VA": "Valor geral", "fit": "Encaixe punt-TOV",
                **{f"z_{c}": CAT_LABELS[c] for c in CATS}}
    c1, c2, c3 = st.columns(3)
    grupos = c1.multiselect("Posição", ["Armador", "Ala", "Ala-pivô", "Pivô"], default=[])
    ordenar = c2.selectbox("Ordenar por (o aspecto que te interessa)", list(ASPECTOS),
                           format_func=lambda k: ASPECTOS[k])
    min_va = c3.slider("Valor mínimo (corta os fracos)", -3.0, 8.0, -1.0, 0.5)
    if grupos:
        fa = fa[fa["Grupo"].isin(grupos)]
    fa = fa[fa["VA"] >= min_va]
    fa_sorted = fa.sort_values(ordenar, ascending=False)
    st.caption(f"{len(fa)} jogadores livres/matcháveis (amostra ≥25 jogos). "
               f"Ordenado por **{ASPECTOS[ordenar]}**.")
    viz = st.radio("Visualização", ["🔥 Calor (tabela)", "🕸️ Radar (comparar)"],
                   horizontal=True, key="fa_viz")
    if viz.startswith("🔥"):
        show(fa, cols=["Jogador", "Pos", "Grupo", "Age", "VA", "fit",
                       "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV",
                       "held_by"],
             sort=ordenar, color_z=True, height=560)
    else:
        from ui_common import radar_chart
        opts = fa_sorted["Jogador"].tolist()
        escolhidos = st.multiselect("Compare até 4 alvos", opts, default=opts[:2],
                                    max_selections=4, key="fa_radar_sel")
        com_time = st.checkbox("Sobrepor o Lobos (média z do top-10)", value=True,
                               key="fa_radar_me")
        REF = "🐺 Lobos (top-10)"
        profiles = {}
        if com_time:
            mr = cached_my_roster()
            profiles[REF] = {c: float(mr[f"z_{c}"].dropna().nlargest(10).mean())
                             for c in CATS}
        for _, r in fa_sorted[fa_sorted["Jogador"].isin(escolhidos)].iterrows():
            profiles[r["Jogador"]] = {c: r[f"z_{c}"] for c in CATS}
        if escolhidos:
            _, mid, _ = st.columns([1, 3, 1])   # quadrado e centrado — radar
            with mid:                            # esticado distorce a comparação
                st.altair_chart(radar_chart(profiles, CATS, reference=REF),
                                use_container_width=False)
            st.caption("Raio = z-score clipado em [−1,5, +3]; anel cheio = média da "
                       "liga (z=0), tracejado externo = z+3. TOV já invertido (mais "
                       "pra fora = menos turnover). O tracejado cinza é o Lobos: "
                       "pontas do alvo que saltam além dele = buraco que ele tapa.")
        else:
            st.info("Escolha ao menos um jogador pra desenhar o radar.")

# ---------- Draft lista crua (seeds) ----------
with tab_draft:
    st.subheader("Draft — lista crua completa")
    st.caption("Todas as dimensões de cada prospecto. Filtre e ordene como quiser.")
    d2 = adv["draft2"].copy()
    DA = {"score": "Nota geral", "pick_NBA": "Pick NBA (mais cedo = melhor)",
          "proj_curva": "Projeção", "opp_mult": "Oportunidade", "vacuo_min": "Vaga no seu time"}
    c1, c2, c3 = st.columns(3)
    poss = c1.multiselect("Posição", sorted(d2["Pos"].dropna().unique()), default=[])
    so_pick = c2.checkbox("Só quem tem pick no draft NBA 2026", value=False)
    ordd = c3.selectbox("Ordenar por", list(DA), format_func=lambda k: DA[k])
    dd = d2.copy()
    if poss:
        dd = dd[dd["Pos"].isin(poss)]
    if so_pick:
        dd = dd[dd["pick_NBA"].notna()]
    asc = ordd == "pick_NBA"
    st.caption(f"{len(dd)} prospectos · ordenado por **{DA[ordd]}**.")
    show(dd, cols=["Prospecto", "Pos", "pick_NBA", "time_final", "proj_curva", "opp_mult",
                   "vacuo_min", "score"], sort=ordd, ascending=asc, bar="score", height=600)

# ---------- LIGA (seeds) ----------
with tab_liga:
    st.subheader("Força da liga por categoria")
    ls = cached_league_strength().sort_values("Total_VA", ascending=False)
    st.markdown("#### 🐺 Onde o Lobos se posiciona (rank por categoria, de 24 times)")
    st.caption("Barra menor = melhor. Rank alto = categoria onde você perde e precisa reforçar.")
    my_ranks = {c: int(ls[c].rank(ascending=False, method="min")[ls["Franquia"] == MY_FRANCHISE].values[0])
                for c in CATS}
    st.bar_chart(pd.Series(my_ranks, name="Seu rank (1=melhor)"), horizontal=True, color="#42a5f5")
    st.divider()
    st.markdown("#### Tabela completa — 🟩 forte · 🟥 fraco · **seu time em azul**")
    lsr = ls.rename(columns={"Total_VA": "Valor total"})
    sty = (lsr.style.map(lambda v: zcolor(v, scale=4), subset=CATS)
           .apply(highlight_mine, subset=["Franquia"]))
    st.dataframe(sty, width="stretch", hide_index=True, height=680)

# ---------- SALÁRIOS (seeds) ----------
with tab_cap:
    st.subheader("Salários da liga (teto $190M)")
    cap = cached_team_cap()
    mine = cap[cap["Franquia"] == MY_FRANCHISE]
    if len(mine):
        m1, m2, m3 = st.columns(3)
        m1.metric("Sua folha (Ano 1)", f"${mine['Folha_M'].values[0]:.1f}M")
        m2.metric("Seu espaço livre", f"${mine['Espaço_M'].values[0]:.1f}M")
        m3.metric("Teto salarial", "$190M")
    st.markdown("#### Folha por time — quem já gastou mais")
    capsort = cap.sort_values("Folha_M", ascending=False)
    st.bar_chart(capsort.set_index("Franquia")["Folha_M"], horizontal=True, color="#ef5350")
    pos = list(capsort["Franquia"]).index(MY_FRANCHISE) + 1 if len(mine) else 0
    if pos:
        st.caption(f"🐺 O Lobos é a **{pos}ª maior folha** de 24 — "
                   f"{'muito comprometido' if pos <= 6 else 'espaço saudável' if pos >= 14 else 'no meio'}.")
    st.divider()
    st.markdown("#### 🐺 Seu elenco — quem come seu cap")
    mr = cached_my_roster().copy()
    mr_paid = mr[mr["salary_y1_m"] > 0].sort_values("salary_y1_m", ascending=False)
    cA, cB = st.columns([1, 1])
    with cA:
        st.bar_chart(mr_paid.set_index("Jogador")["salary_y1_m"], horizontal=True, color="#ffa726")
    with cB:
        show(mr_paid, cols=["Jogador", "Pos", "salary_y1_m", "VA"], sort="salary_y1_m", height=340)
    st.divider()
    st.markdown("#### Tabela da liga — espaço de cada franquia")
    d = cap.sort_values("Espaço_M", ascending=False).rename(columns=NOMES)
    st.dataframe(
        d.style.map(lambda v: f"background-color:{'#1b5e20' if v > 20 else '#b71c1c' if v < 5 else ''}"
                    + (";color:white" if (v > 20 or v < 5) else ""), subset=["Espaço $M"])
        .apply(highlight_mine, subset=["Franquia"]),
        width="stretch", hide_index=True, height=420)

# ---------- NBA Médias & Métricas (marts dbt) ----------
PG = {"pts_pg": "PTS", "trb_pg": "REB", "ast_pg": "AST", "stocks_pg": "STOCKS",
      "three_p_pg": "3PM", "plus_minus_pg": "+/-", "tov_pg": "TOV"}
ZC = {"z_" + k.removesuffix("_pg"): v for k, v in PG.items()}  # mesmo vocabulário do PG

with tab_nba1:
    seasons_df = q("select distinct season from analytics_marts.fct_player_fantasy_value_season order by season desc")
    if db_guard(seasons_df):
        seasons = seasons_df["season"].tolist()
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
        if db_guard(base):
            view = base[base["jogos"] >= min_g].copy()
            st.markdown("#### Médias por-jogo (padrão)")
            std_cols = ["player_name", "jogos", "min"] + list(PG.keys())
            st.dataframe(view[std_cols].rename(columns=PG).sort_values("PTS", ascending=False),
                         width="stretch", hide_index=True, height=320)
            st.markdown("#### Métricas avançadas (mais profundas)")
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
            zrow = q(f"""select z_pts,z_trb,z_ast,z_stocks,z_three_p,z_plus_minus,z_tov
                         from analytics_marts.fct_player_fantasy_value_season
                         where player_name = '{who.replace("'", "''")}' and season = '{season}'""")
            if zrow is not None and not zrow.empty:
                prof = pd.DataFrame({"categoria": list(ZC.values()),
                                     "z-score": [zrow.iloc[0][k] for k in ZC]}).set_index("categoria")
                st.caption("Perfil por categoria (z>0 = acima da média da liga)")
                st.bar_chart(prof, height=240)

# ---------- NBA Valor Fantasy (marts dbt) ----------
with tab_nba2:
    st.caption("Valor por z-score nas 7 categorias (TOV invertido). Base pra draft/keepers/trocas.")
    df = q("""
        select player_name, games_played, is_reference_pool,
               z_pts, z_trb, z_ast, z_stocks, z_three_p, z_plus_minus, z_tov
        from analytics_marts.fct_player_fantasy_value_season
    """)
    if db_guard(df):
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
            v.sort_values("valor", ascending=False)[
                ["player_name", "games_played", "valor"] + list(ZC.keys())].head(60),
            width="stretch", hide_index=True,
            column_config={zc: st.column_config.NumberColumn(lab, format="%.2f")
                           for zc, lab in ZC.items()})
        with st.expander("🏅 Líderes por categoria (top 5)"):
            cols = st.columns(len(ZC))
            for (zc, lab), col in zip(ZC.items(), cols):
                col.markdown(f"**{lab}**")
                for _, x in v.nlargest(5, zc)[["player_name", zc]].iterrows():
                    col.caption(f"{x['player_name']} ({x[zc]:.1f})")

# ---------- College (marts dbt) ----------
with tab_coll:
    cseasons_df = q("select distinct season from analytics_intermediate.int_prospect__college_stats order by season desc")
    if db_guard(cseasons_df):
        cs = st.selectbox("Temporada (college)", cseasons_df["season"].tolist(), key="coll_season")
        coll = q(f"""
            select player_name, school, class, archetype,
                   pts_per_40, trb_per_40, ast_per_40, stocks_per_40, three_p_per_40, tov_per_40,
                   ts_pct, usg_pct, team_sos
            from analytics_intermediate.int_prospect__college_stats
            where season = '{cs}' order by pts_per_40 desc
        """)
        if db_guard(coll):
            st.markdown(f"#### Prospectos em {cs} — médias por-40-min")
            st.dataframe(coll, width="stretch", hide_index=True, height=320)
            st.markdown("#### Evolução de um prospecto (multi-temporada)")
            multi = q("""
                select cbb_id, player_name from analytics_intermediate.int_prospect__college_stats
                group by cbb_id, player_name having count(*) >= 2 order by player_name
            """)
            if db_guard(multi):
                lbl = dict(zip(multi["player_name"] + " (" + multi["cbb_id"] + ")", multi["cbb_id"]))
                pick = st.selectbox("Prospecto", list(lbl.keys()), key="coll_evo")
                traj = q(f"""
                    select season, pts_per_40, trb_per_40, ast_per_40, stocks_per_40, three_p_per_40
                    from analytics_intermediate.int_prospect__college_stats
                    where cbb_id = '{lbl[pick]}' order by season
                """)
                if db_guard(traj):
                    traj = traj.set_index("season")
                    traj.columns = ["PTS/40", "REB/40", "AST/40", "STK/40", "3PM/40"]
                    st.line_chart(traj, height=300)

# ---------- Scouting de Draft (marts dbt) ----------
with tab_scout:
    st.caption("Projeção NBA = desfecho médio dos comps históricos + sinal de confiança (D-33).")
    df = q("""
        select prospect_name, prospect_season, prospect_archetype, confidence,
               n_comps_with_outcome, n_comps_with_6cat, mean_comp_distance,
               proj_pg_pts, proj_pg_trb, proj_pg_ast, proj_pg_stocks, proj_pg_fg3, proj_pg_tov,
               proj_win_shares, proj_vorp
        from analytics_marts.fct_prospect_scouting
    """)
    if db_guard(df):
        c1, c2 = st.columns(2)
        confs = c1.multiselect("Confiança", ["alta", "media", "baixa"],
                               default=["alta", "media", "baixa"])
        archs = c2.multiselect("Arquétipo", sorted(df["prospect_archetype"].dropna().unique()),
                               default=sorted(df["prospect_archetype"].dropna().unique()))
        view = df[df["confidence"].isin(confs) & df["prospect_archetype"].isin(archs)]
        st.dataframe(view.sort_values("proj_win_shares", ascending=False, na_position="last"),
                     width="stretch", hide_index=True)

# ---------- Comps (marts dbt) ----------
with tab_comps:
    prospects = q("select distinct prospect_id, prospect_name from analytics_intermediate.int_prospect__comps order by prospect_name")
    if db_guard(prospects):
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
        if db_guard(comps):
            st.dataframe(comps, width="stretch", hide_index=True)

# ---------- Notícias (RSS; jogadores do pool via DB com fallback p/ seeds) ----------
with tab_news:
    st.caption("Fontes: ESPN, Yahoo, CBS (RSS grátis). Sem Twitter/Shams (API paga).")

    @st.cache_data(ttl=900)
    def _news():
        return get_nba_news()

    news = _news()
    if news.empty:
        st.warning("Não consegui buscar as notícias agora.")
    else:
        pool_df = q("select distinct player_name from analytics_marts.fct_player_fantasy_value_season where is_reference_pool")
        if pool_df is not None and not pool_df.empty:
            players = pool_df["player_name"].dropna().tolist()
        else:   # fallback sem DB: pool de rotação dos seeds (parse tolerante _f —
            # BBR pode deixar linha de header repetido passar; astype quebraria)
            players = eng.reference_pool()["Player"].dropna().tolist()
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
