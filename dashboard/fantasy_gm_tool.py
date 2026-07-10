"""
Protótipo de apoio à decisão — Free Agency + Draft (Bandeja de 3).

Ferramenta pra usar AO VIVO durante FA e draft: mostra o valor do seu elenco por
categoria, os melhores alvos de FA (com flag de match), o board de draft ajustado por
oportunidade e o cap da liga. Roda sobre o `fantasy_engine` (lê seeds, sem DB).

Rodar:
    streamlit run dashboard/fantasy_gm_tool.py   ->  http://localhost:8501

Dado: reflete o seed atual (snapshot do scraper). Pra atualizar pós-trocas:
    python src/scraping/fantasy_gm.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st
from fantasy_engine import Engine, CATS, MY_FRANCHISE

st.set_page_config(page_title="Bandeja de 3 — GM Tool", layout="wide")


from fa_draft_engine import FADraft


@st.cache_data
def load():
    return Engine()


@st.cache_data
def load_advanced():
    fd = FADraft()
    fd.build_all()          # (k) computa e persiste em data_cache/ uma vez
    wd = fd.simulate_weights()   # dict cat->Δwinrate
    weights_df = (pd.DataFrame({"categoria": list(wd.keys()),
                                "peso_dwinrate": list(wd.values())})
                  .sort_values("peso_dwinrate", ascending=False))
    return {
        "weights": weights_df, "base_wr": fd.base_winrate,
        "fa_board": fd.fa_board(30), "rivals": fd.rival_competition(),
        "waiver": fd.waiver_watch(), "curve": fd.pick_curve(),
        "price": fd.pick_price(), "draft2": fd.draft_board2(30),
        "buy": fd.pick_buy_analysis(),
    }


eng = load()
adv = load_advanced()

# ---------- helpers de exibição (nomes claros + cores + ordenação) ----------
# tradução de colunas técnicas -> português simples
NOMES = {
    "z_PTS": "Pontos", "z_REB": "Rebotes", "z_AST": "Assist.", "z_STOCKS": "Roubo+Toco",
    "z_3PM": "Bolas 3", "z_TOV": "Turnovers", "salary_y1_m": "Salário $M", "VA": "Valor",
    "va_over_repl": "Valor extra", "fit_sim": "Encaixe", "injury_disc": "Saúde",
    "score": "Nota", "pos_group": "Grupo", "fit": "Encaixe", "held_by": "Dono atual",
    "proj_curva": "Projeção", "opp_mult": "Oportun.", "vacuo_min": "Vaga de minutos",
    "pick_NBA": "Pick NBA", "time_final": "Time NBA", "nba_team": "Time NBA",
    "posicao_americana": "Pos (US)", "cap_livre_M": "Cap livre $M",
    "categorias_fracas": "Fraco em", "ameaca_FA": "Risco de brigar",
    "corte_provavel": "Provável corte", "Total_VA": "Valor total",
    "Folha_M": "Folha $M", "Espaço_M": "Espaço $M", "Age": "Idade",
}
# colunas de z-score (verde=forte, vermelho=fraco): -1.5..+1.5 -> vermelho..verde
ZCOLS = {"Pontos", "Rebotes", "Assist.", "Roubo+Toco", "Bolas 3", "Turnovers"}


def _zcolor(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    if v >= 0.75:  return "background-color:#1b5e20;color:white"   # elite
    if v >= 0.25:  return "background-color:#4caf50"               # bom
    if v > -0.25:  return "background-color:#9e9e9e"               # médio
    if v > -0.75:  return "background-color:#ef9a9a"               # fraco
    return "background-color:#b71c1c;color:white"                  # buraco


def show(df, cols=None, sort=None, ascending=False, color_z=False, bar=None, pct=None, height=None):
    """Renomeia p/ PT, seleciona/ordena colunas e aplica cor. bar=coluna p/ barra de nota."""
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
    sty = d.style.map(_zcolor, subset=zc) if zc else d.style
    cfg = {}
    if bar:
        b = NOMES.get(bar, bar)
        if b in d.columns:
            cfg[b] = st.column_config.ProgressColumn(
                b, format="%.1f", min_value=float(d[b].min()), max_value=float(d[b].max()))
    kw = {"width": "stretch", "hide_index": True, "column_config": cfg}
    if height:
        kw["height"] = height
    st.dataframe(sty, **kw)


st.title("🏀 Bandeja de 3 — Central do GM do Lobos")
st.caption("Como ler os números: **Valor / Nota** — quanto maior, melhor. "
           "**Categorias coloridas** — 🟩 verde = você é forte · 🟥 vermelho = ponto fraco a reforçar.")

(tab_time, tab_fa2, tab_draft2, tab_fa, tab_draft, tab_liga, tab_cap) = st.tabs(
    ["🧢 Meu time", "🎯 Free Agency", "🏆 Draft", "🔎 FA (lista crua)", "🔎 Draft (lista crua)", "🏆 Liga", "💰 Salários"]
)

# ---------- MEU TIME ----------
with tab_time:
    st.subheader(f"Elenco do {MY_FRANCHISE}")
    mr = eng.my_roster()
    # perfil por categoria: média em vez de soma, mais intuitivo (0 = média da liga)
    prof = pd.DataFrame({
        "Categoria": ["Pontos", "Rebotes", "Assist.", "Roubo+Toco", "Bolas 3", "Turnovers"],
        "Força do time": [round(mr[f"z_{c}"].dropna().nlargest(10).mean(), 2) for c in CATS],
    }).sort_values("Força do time")
    st.markdown("#### Onde o time é forte e fraco")
    st.caption("Barra pra **direita** = você ganha essa categoria da liga. Pra **esquerda** = precisa reforçar. "
               "(0 = na média da liga.)")
    st.bar_chart(prof.set_index("Categoria"), horizontal=True, color="#42a5f5")
    fraca = prof.iloc[0]["Categoria"]
    st.info(f"🎯 Seu maior buraco hoje: **{fraca}** — priorize em FA e no draft.")
    st.markdown("#### Elenco (verde = manda bem na categoria · vermelho = fraco)")
    show(mr, cols=["Jogador", "Pos", "Age", "salary_y1_m", "VA",
                   "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_TOV"],
         sort="VA", color_z=True, bar="VA", height=680)

# ---------- FREE AGENCY (2.0) ----------
with tab_fa2:
    st.subheader("🎯 Melhores alvos de Free Agency")
    st.markdown("#### Quanto cada categoria vale PRA VOCÊ vencer")
    st.caption("Barra maior = ganhar nessa categoria te dá mais vitórias. É o que o ranking de alvos prioriza.")
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
    st.markdown("#### Ranking de alvos (livres na liga, já ponderado pelo que você precisa)")
    st.caption("**Nota** = o quão bom é o alvo pra você (junta valor do jogador + encaixe no que falta − risco de lesão). "
               "**Saúde** = 100% sem lesão. Ordenado do melhor pro pior.")
    show(adv["fa_board"], cols=["Jogador", "Pos", "Age", "score", "VA", "va_over_repl", "injury_disc"],
         sort="score", bar="score", pct=["injury_disc"], height=560)
    with st.expander("⚔️ Quem mais briga pelos MESMOS alvos que você (rivais)"):
        show(adv["rivals"], cols=["Franquia", "cap_livre_M", "categorias_fracas", "ameaca_FA"], sort="cap_livre_M")
    with st.expander("🔔 Times lotados que vão CORTAR bons jogadores (waiver)"):
        show(adv["waiver"], cols=["Franquia", "corte_provavel", "VA"], sort="VA")

# ---------- DRAFT (2.0) ----------
with tab_draft2:
    st.subheader("🏆 Board de Draft 2026 (talento × oportunidade)")
    st.caption("**Nota** junta: onde o cara foi escolhido no draft NBA + se cai num time que dá minutos "
               "(rebuild) + se preenche uma vaga no seu elenco.")
    d2 = adv["draft2"].copy()
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        st.markdown("#### Top 15 prospectos (por Nota)")
        top15 = d2.sort_values("score", ascending=False).head(15)
        st.bar_chart(top15.set_index("Prospecto")["score"], horizontal=True, color="#ab47bc")
    with cc2:
        st.markdown("#### Valor × posição no draft")
        st.caption("Alto num pick tardio (canto sup. direito) = **sleeper**; baixo num pick alto = risco.")
        sc = d2[d2["pick_NBA"].notna()].rename(columns={"pick_NBA": "Pick NBA", "score": "Nota"})
        st.scatter_chart(sc, x="Pick NBA", y="Nota", color="#ab47bc", height=340)
    st.markdown("#### Board completo")
    show(d2, cols=["Prospecto", "Pos", "pick_NBA", "time_final", "score", "proj_curva", "opp_mult", "vacuo_min"],
         sort="score", bar="score", height=380)
    st.divider()
    st.markdown("#### Vale a pena COMPRAR uma pick numa troca?")
    st.caption("Compara o que a pick tende a produzir com o preço real (em jogadores) que ela custou nas trades da liga.")
    buy = adv["buy"].rename(columns={
        "pick": "Pick nº", "rodada": "Rodada", "prod_esperada": "Produção esperada",
        "custo_pick_M": "Custo em jogadores $M", "salario_rookie_M": "Salário rookie $M",
        "vale_comprar": "Vale comprar?"})
    st.dataframe(
        buy.style.map(lambda v: "background-color:#1b5e20;color:white" if v == "SIM"
                      else "background-color:#5d4037" if v == "só se barato" else "",
                      subset=["Vale comprar?"]),
        width="stretch", hide_index=True)
    st.info("💡 Regra rápida: pick de 1ª rodada custa ~**$34M** em jogadores — só vale nas **~15 primeiras** "
            "(top-15). Pick tardia de 1ª (#20-30): só se baratear. Pick de 2ª (~$14M) rende bem por ser barata.")

# ---------- FA lista crua (todos os aspectos) ----------
with tab_fa:
    st.subheader("Free Agency — lista crua (todos os aspectos)")
    st.caption("Todas as categorias coloridas + filtros. **Dono atual** = franquia que segura o passe "
               "(pode cobrir a oferta se estiver no playoff); '(livre)' = sem dono.")
    fa = eng.fa_targets(120)
    ASPECTOS = {"VA": "Valor geral", "fit": "Encaixe punt-TOV", "z_PTS": "Pontos", "z_REB": "Rebotes",
                "z_AST": "Assist.", "z_STOCKS": "Roubo+Toco", "z_3PM": "Bolas 3", "z_TOV": "Turnovers"}
    c1, c2, c3 = st.columns(3)
    grupos = c1.multiselect("Posição", ["Armador", "Ala", "Ala-pivô", "Pivô"], default=[])
    ordenar = c2.selectbox("Ordenar por (o aspecto que te interessa)", list(ASPECTOS),
                           format_func=lambda k: ASPECTOS[k])
    min_va = c3.slider("Valor mínimo (corta os fracos)", -3.0, 8.0, -1.0, 0.5)
    if grupos:
        fa = fa[fa["Grupo"].isin(grupos)]
    fa = fa[fa["VA"] >= min_va]
    st.caption(f"{len(fa)} jogadores livres/matcháveis (amostra ≥25 jogos). Ordenado por **{ASPECTOS[ordenar]}**.")
    show(fa, cols=["Jogador", "Pos", "Grupo", "Age", "VA", "fit",
                   "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_TOV", "held_by"],
         sort=ordenar, color_z=True, height=560)

# ---------- Draft lista crua (completa) ----------
with tab_draft:
    st.subheader("Draft — lista crua completa (94 prospectos)")
    st.caption("Todas as dimensões de cada prospecto: pick no draft NBA, time que ele vai, projeção pela curva, "
               "oportunidade e a vaga que abre no seu elenco. Filtre e ordene como quiser.")
    d2 = adv["draft2"].copy()
    DA = {"score": "Nota geral", "pick_NBA": "Pick NBA (mais cedo = melhor)", "proj_curva": "Projeção",
          "opp_mult": "Oportunidade", "vacuo_min": "Vaga no seu time"}
    c1, c2, c3 = st.columns(3)
    poss = c1.multiselect("Posição", sorted(d2["Pos"].dropna().unique()), default=[])
    so_pick = c2.checkbox("Só quem tem pick no draft NBA 2026", value=False)
    ordd = c3.selectbox("Ordenar por", list(DA), format_func=lambda k: DA[k])
    dd = d2.copy()
    if poss:
        dd = dd[dd["Pos"].isin(poss)]
    if so_pick:
        dd = dd[dd["pick_NBA"].notna()]
    asc = ordd == "pick_NBA"   # pick menor = melhor
    st.caption(f"{len(dd)} prospectos · ordenado por **{DA[ordd]}**.")
    show(dd, cols=["Prospecto", "Pos", "pick_NBA", "time_final", "proj_curva", "opp_mult", "vacuo_min", "score"],
         sort=ordd, ascending=asc, bar="score", height=600)

# ---------- LIGA ----------
with tab_liga:
    st.subheader("Força da liga por categoria")
    ls = eng.league_strength().sort_values("Total_VA", ascending=False)
    catcols = ["PTS", "REB", "AST", "STOCKS", "3PM", "TOV"]
    # onde VOCÊ se posiciona: rank por categoria (1 = melhor de 24)
    st.markdown("#### 🐺 Onde o Lobos se posiciona (rank por categoria, de 24 times)")
    st.caption("Barra menor = melhor. Rank alto = categoria onde você perde e precisa reforçar.")
    my_ranks = {c: int(ls[c].rank(ascending=False, method="min")[ls["Franquia"] == MY_FRANCHISE].values[0])
                for c in catcols}
    st.bar_chart(pd.Series(my_ranks, name="Seu rank (1=melhor)"), horizontal=True, color="#42a5f5")
    st.divider()
    st.markdown("#### Tabela completa — 🟩 forte · 🟥 fraco · **seu time em azul**")

    def _catcolor(v):
        if v >= 3: return "background-color:#1b5e20;color:white"
        if v >= 1: return "background-color:#4caf50"
        if v > -1: return "background-color:#9e9e9e"
        if v > -3: return "background-color:#ef9a9a"
        return "background-color:#b71c1c;color:white"

    lsr = ls.rename(columns={"Total_VA": "Valor total"})
    sty = (lsr.style.map(_catcolor, subset=catcols)
           .apply(lambda s: ["background-color:#0d47a1;color:white;font-weight:bold"
                             if v == MY_FRANCHISE else "" for v in s], subset=["Franquia"]))
    st.dataframe(sty, width="stretch", hide_index=True, height=680)

# ---------- CAP ----------
with tab_cap:
    st.subheader("Salários da liga (teto $190M)")
    cap = eng.team_cap()
    mine = cap[cap["Franquia"] == MY_FRANCHISE]
    if len(mine):
        m1, m2, m3 = st.columns(3)
        m1.metric("Sua folha (Ano 1)", f"${mine['Folha_M'].values[0]:.1f}M")
        m2.metric("Seu espaço livre", f"${mine['Espaço_M'].values[0]:.1f}M")
        m3.metric("Teto salarial", "$190M")
    st.markdown("#### Folha por time — quem já gastou mais (seu time destacado no texto)")
    capsort = cap.sort_values("Folha_M", ascending=False)
    st.bar_chart(capsort.set_index("Franquia")["Folha_M"], horizontal=True, color="#ef5350")
    pos = list(capsort["Franquia"]).index(MY_FRANCHISE) + 1 if len(mine) else 0
    if pos:
        st.caption(f"🐺 O Lobos é a **{pos}ª maior folha** de 24 — "
                   f"{'muito comprometido' if pos <= 6 else 'espaço saudável' if pos >= 14 else 'no meio'}.")
    st.divider()
    st.markdown("#### 🐺 Seu elenco — quem come seu cap")
    mr = eng.my_roster().copy()
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
        .apply(lambda s: ["background-color:#0d47a1;color:white;font-weight:bold"
                          if v == MY_FRANCHISE else "" for v in s], subset=["Franquia"]),
        width="stretch", hide_index=True, height=420)
