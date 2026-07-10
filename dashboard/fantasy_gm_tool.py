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

st.title("🏀 Bandeja de 3 — Ferramenta de GM (FA + Draft)")
st.caption("Contexto punt-TOV • valor = z_total − z_tov • pesos vindos de simulação de winrate")

(tab_time, tab_fa2, tab_draft2, tab_fa, tab_draft, tab_liga, tab_cap) = st.tabs(
    ["🧢 Meu time", "🎯 FA 2.0", "🏆 Draft 2.0", "🆓 FA (básico)", "🎓 Draft (básico)", "🏆 Liga", "💰 Cap"]
)

# ---------- MEU TIME ----------
with tab_time:
    st.subheader(f"Elenco — {MY_FRANCHISE}")
    mr = eng.my_roster()
    st.dataframe(mr, use_container_width=True, hide_index=True)
    # perfil de categoria (soma dos titulares)
    prof = {c: round(mr[f"z_{c}"].dropna().nlargest(10).sum(), 1) for c in CATS}
    st.markdown("**Perfil por categoria (soma z do top-10):**")
    st.bar_chart(pd.Series(prof))
    st.info("VA = valor punt-TOV. Vermelho nas cats = onde você precisa comprar/draftar.")

# ---------- FA 2.0 (pesos de simulação + valor sobre reposição) ----------
with tab_fa2:
    st.subheader("🎯 Free Agency 2.0 — pesos vindos de SIMULAÇÃO de winrate")
    w = adv["weights"].copy()
    st.markdown(f"**Winrate base do Lobos: `{adv['base_wr']*100:.1f}%`** por confronto. "
                "Cada barra = ganho de winrate ao somar +1σ naquela categoria "
                "(quanto maior, mais essa cat move a agulha PRA VOCÊ).")
    st.bar_chart(w.set_index("categoria")["peso_dwinrate"])
    top_lever = w.sort_values("peso_dwinrate", ascending=False).iloc[0]
    st.success(f"Maior alavanca: **{top_lever['categoria']}** "
               f"(+{top_lever['peso_dwinrate']*100:.1f}pp de winrate por +1σ). "
               "É pra ISSO que o board abaixo pondera os alvos.")
    st.divider()
    st.markdown("**Board de FA** — `score = 0.5·(VA − reposição posicional) + 0.5·fit_sim`, "
                "com desconto de lesão. Só jogadores valorados **fora dos 24 rosters**.")
    st.dataframe(adv["fa_board"], use_container_width=True, hide_index=True)
    st.caption("va_over_repl = valor acima do 'nível de reposição' da posição (top-3 FA daquele grupo). "
               "fit_sim = quanto o cara pontua nas cats que a simulação diz que te dão vitória.")
    with st.expander("⚔️ Concorrência rival — quem mais precisa das MESMAS cats que você"):
        st.dataframe(adv["rivals"], use_container_width=True, hide_index=True)
    with st.expander("🔔 Waiver watch — franquias acima do limite de roster (vão cortar bons jogadores)"):
        st.dataframe(adv["waiver"], use_container_width=True, hide_index=True)

# ---------- DRAFT 2.0 (curva de pick × oportunidade × preço real) ----------
with tab_draft2:
    st.subheader("🏆 Draft Board 2.0 — curva de pick × oportunidade × vácuo de minutos")
    st.caption("Projeção calibrada pela produção HISTÓRICA por nº de pick (classes 2016+), "
               "ajustada pela situação NBA 2026 (rebuild = minutos) e vácuo no seu elenco.")
    st.dataframe(adv["draft2"], use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Curva de pick** (produção esperada por nº)")
        st.line_chart(adv["curve"].set_index("pick")["expected_prod"])
    with c2:
        st.markdown("**Preço real de pick** (minerado das trades da liga)")
        st.dataframe(adv["price"], use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("**Vale COMPRAR uma pick?** — produção esperada do slot × preço real em jogadores")
    buy = adv["buy"]
    st.dataframe(buy.style.map(
        lambda v: "background-color:#1b5e20" if v == "SIM" else "", subset=["vale_comprar"]),
        use_container_width=True, hide_index=True)
    st.info("1ª rodada custa ~$34M em jogadores. Só vale se o slot projeta ≥14 de produção "
            "(≈ top-15). Late-1st (#20-30) = só se o preço cair. 2ª rodada (~$14M) rende bem por ser barata.")

# ---------- FREE AGENCY ----------
with tab_fa:
    st.subheader("Alvos de Free Agency (ranqueados por fit punt-TOV)")
    c1, c2 = st.columns(2)
    only_gettable = c1.checkbox("Só gettable (não segurado por time forte)", value=False)
    min_3pm = c2.slider("z_3PM mínimo (mira atirador)", -2.0, 3.0, -2.0, 0.5)
    fa = eng.fa_targets(60)
    fa = fa[fa["z_3PM"] >= min_3pm]
    st.dataframe(fa, use_container_width=True, hide_index=True)
    st.caption("held_by = franquia que segura o $0 (pode dar match se for playoff). "
               "'(livre)' = fora de qualquer roster.")

# ---------- DRAFT ----------
with tab_draft:
    st.subheader("Board de draft — ajustado por OPORTUNIDADE")
    st.caption("Talento × situação do time NBA final (rebuild = minutos; contender lotado = enterrado).")
    db = eng.draft_board(40)
    st.dataframe(db, use_container_width=True, hide_index=True)
    st.warning("Projeção de prospecto tem confiança BAIXA (comps 2026). Use como direção, não cravado.")

# ---------- LIGA ----------
with tab_liga:
    st.subheader("Força da liga por categoria (rival scan)")
    ls = eng.league_strength()
    st.dataframe(ls, use_container_width=True, hide_index=True)
    st.caption("Onde você ganha da maioria = suas categorias-alvo. "
               "Times fortes onde você é fraco = parceiros de troca.")

# ---------- CAP ----------
with tab_cap:
    st.subheader("Cap da liga (teto $190M)")
    cap = eng.team_cap()
    st.dataframe(
        cap.style.map(
            lambda v: f"background-color:{'#1b5e20' if v > 20 else '#b71c1c' if v < 5 else ''}",
            subset=["Espaço_M"]),
        use_container_width=True, hide_index=True)
    mine = cap[cap["Franquia"] == MY_FRANCHISE]
    if len(mine):
        st.metric("Seu espaço de cap", f"${mine['Espaço_M'].values[0]:.1f}M")
