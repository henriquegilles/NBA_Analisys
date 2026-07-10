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


@st.cache_data
def load():
    return Engine()


eng = load()

st.title("🏀 Bandeja de 3 — Ferramenta de GM (FA + Draft)")
st.caption("Contexto punt-TOV • valor = z_total − z_tov • dado do último scrape do FantasyGM")

tab_time, tab_fa, tab_draft, tab_liga, tab_cap = st.tabs(
    ["🧢 Meu time", "🆓 Free Agency", "🎓 Draft", "🏆 Liga", "💰 Cap"]
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
    st.dataframe(cap.style.background_gradient(subset=["Espaço_M"], cmap="RdYlGn"),
                 use_container_width=True, hide_index=True)
    mine = cap[cap["Franquia"] == MY_FRANCHISE]
    if len(mine):
        st.metric("Seu espaço de cap", f"${mine['Espaço_M'].values[0]:.1f}M")
