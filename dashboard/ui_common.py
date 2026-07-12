"""
Módulo comum do painel unificado (Bandeja de 3) — extraído na fusão de
app.py + fantasy_gm_tool.py (Rodada 6, Fase 2) pra zerar duplicação:

  - acesso ao Postgres com FALLBACK GRACIOSO: banco fora → aviso claro;
    erro de SQL/schema → o erro REAL aparece (não é mascarado como "banco fora");
    falha nunca fica cacheada (só sucesso entra no cache)
  - loaders cacheados do motor de seeds (Engine, FADraft, Predicts) + wrappers
    cacheados dos métodos pesados (evita recomputar a cada interação de widget)
  - helpers de exibição (tradução PT, cores de z-score, show())
"""
from __future__ import annotations
import os

import pandas as pd
import streamlit as st

from fantasy_engine import CATS, MY_FRANCHISE

# ---------- Postgres (marts dbt) com fallback ----------

DB_HINT = ("⚠️ Postgres fora do ar — esta aba lê os marts dbt. Suba o banco "
           "(`docker compose up -d postgres`) e rode `dbt run --profiles-dir .dbt`. "
           "As abas baseadas em seeds continuam funcionando.")

def _db_kw() -> dict:
    # lido a CADA chamada (não no import): env pode mudar em runtime (testes,
    # troca de banco) e um dict congelado no import ignoraria isso
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
    """Ping curto e cacheado (15s): todas as abas de DB curto-circuitam num run
    só quando o banco está fora (senão cada query pagaria 3s de connect-timeout)."""
    import psycopg2
    try:
        with psycopg2.connect(**{**_db_kw(), "connect_timeout": 2}) as c:
            c.cursor().execute("select 1")
        return True
    except Exception:
        return False


@st.cache_data(ttl=300)
def _q_ok(sql: str) -> pd.DataFrame:
    """Só SUCESSO entra no cache — exceção propaga e nada é memoizado
    (uma falha transitória não pode pregar o aviso por 5 minutos)."""
    return pd.read_sql_query(sql, _conn())


def reset_db_caches():
    """Descarta conexão e resultados cacheados (usado pelo smoke-test e após
    restart do banco). Fecha a conexão antes de soltar (senão vaza socket)."""
    try:
        _conn().close()
    except Exception:
        pass
    _conn.clear()
    _q_ok.clear()
    db_alive.clear()


def q(sql: str) -> pd.DataFrame | None:
    """Query nos marts. None = banco indisponível (a aba mostra DB_HINT via
    db_guard). Erro de SQL/schema com o banco DE PÉ vira st.error com a causa
    real — o diagnóstico 'banco fora' não pode mascarar um typo de coluna."""
    if not db_alive():
        return None
    for attempt in (1, 2):
        try:
            return _q_ok(sql)
        except Exception as e:
            # conexão cacheada pode ter morrido (restart do PG): recicla e
            # tenta 1x com conexão fresca antes de concluir qualquer coisa
            try:
                _conn().close()
            except Exception:
                pass
            _conn.clear()
            if attempt == 2:
                if db_alive():
                    st.error(f"Erro na consulta (o banco está DE PÉ — provável "
                             f"mart não construído ou SQL): {e}")
                    return pd.DataFrame()   # sentinela ≠ None: não é 'banco fora'
                return None
    return None


def db_guard(df: pd.DataFrame | None) -> bool:
    """True se o dado veio e não está vazio; None → aviso padrão de banco fora."""
    if df is None:
        st.warning(DB_HINT)
        return False
    return not df.empty


# ---------- motor de seeds (sempre disponível) ----------

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
    wd = fd.simulate_weights()   # dict cat -> Δwinrate (fa_board depende dos pesos)
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


@st.cache_resource
def load_predicts():
    from predicts import Predicts
    return Predicts(load_engine())


# wrappers cacheados dos métodos pesados: os corpos de TODAS as abas executam a
# cada rerun do Streamlit — sem isso, mover um slider recalcula tudo de novo.

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


# ---------- helpers de exibição ----------

NOMES = {
    "z_PTS": "Pontos", "z_REB": "Rebotes", "z_AST": "Assist.", "z_STOCKS": "Roubo+Toco",
    "z_3PM": "Bolas 3", "z_PM": "Plus/Minus", "z_TOV": "Turnovers", "salary_y1_m": "Salário $M", "VA": "Valor",
    "va_over_repl": "Valor extra", "fit_sim": "Encaixe", "injury_disc": "Saúde",
    "ctx_mult": "Contexto 26-27",
    "score": "Nota", "pos_group": "Grupo", "fit": "Encaixe", "held_by": "Dono atual",
    "proj_curva": "Projeção", "opp_mult": "Oportun.", "vacuo_min": "Vaga de minutos",
    "pick_NBA": "Pick NBA", "time_final": "Time NBA", "nba_team": "Time NBA",
    "posicao_americana": "Pos (US)", "cap_livre_M": "Cap livre $M",
    "categorias_fracas": "Fraco em", "ameaca_FA": "Risco de brigar",
    "corte_provavel": "Provável corte", "Total_VA": "Valor total",
    "Folha_M": "Folha $M", "Espaço_M": "Espaço $M", "Age": "Idade",
}
# derivados de NOMES — uma fonte de verdade pros rótulos das 6 categorias
CAT_LABELS = {c: NOMES[f"z_{c}"] for c in CATS}
ZCOLS = set(CAT_LABELS.values())


def zcolor(v, scale: float = 1.0):
    """Cor de z-score: 🟩 forte … 🟥 buraco. scale ajusta os cortes (ex.: scale=4
    pra somas de time, onde ±1/±3 fazem o papel de ±0.25/±0.75)."""
    try:
        v = float(v) / scale
    except (TypeError, ValueError):
        return ""
    if v >= 0.75:  return "background-color:#1b5e20;color:white"   # elite
    if v >= 0.25:  return "background-color:#4caf50"               # bom
    if v > -0.25:  return "background-color:#9e9e9e"               # médio
    if v > -0.75:  return "background-color:#ef9a9a"               # fraco
    return "background-color:#b71c1c;color:white"                  # buraco


def highlight_mine(s):
    """Styler p/ destacar a linha do Lobos em tabelas de liga."""
    return ["background-color:#0d47a1;color:white;font-weight:bold"
            if v == MY_FRANCHISE else "" for v in s]


# paleta categórica validada p/ superfície escura (dataviz skill, 4 slots, PASS
# em banda de luminância / croma / CVD / contraste). Ordem FIXA — nunca ciclar.
RADAR_SERIES = ["#3987e5", "#199e70", "#c98500", "#9085e9"]
RADAR_REF = "#c3c2b7"          # contorno de referência (Lobos) — neutro, tracejado


def radar_chart(profiles: dict, cats: list, reference: str | None = None,
                size: int = 440):
    """Radar de z-scores por categoria (Altair puro — sem plotly no projeto).
    profiles: {nome: {cat: z}} — o item `reference` (ex.: Lobos) vira contorno
    NEUTRO tracejado; os demais recebem a paleta fixa. QUADRADO por construção
    (width=height=size — radar esticado mente na comparação entre eixos).
    r = z clipado em [-1.5, +3] deslocado pra 0..4.5; anel cheio = média da
    liga (z=0). TOV já chega invertido do motor."""
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
        return [{"quem": name, "cat": CAT_LABELS.get(c, c),
                 "z": None if pd.isna(prof.get(c)) else round(float(prof.get(c)), 2),
                 "x": xy(c, prof.get(c, 0.0))[0], "y": xy(c, prof.get(c, 0.0))[1],
                 "ordem": i}
                for i, c in enumerate(cats + cats[:1])]

    players = {k: v for k, v in profiles.items() if k != reference}
    df = pd.DataFrame([r for nm, pf in players.items() for r in poly(nm, pf)])

    grid_rows = []                                     # anéis: z=0 (sólido) e z=+3
    for z_ring, dash in [(0.0, [1, 0]), (3.0, [4, 4])]:
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            r = z_ring - LO
            grid_rows.append({"anel": f"z{z_ring}", "dash": str(dash),
                              "x": r * math.sin(a), "y": r * math.cos(a), "ordem": k})
    grid = pd.DataFrame(grid_rows)

    lab_rows = []
    for c in cats:
        x, y = xy(c, HI)
        lab_rows.append({"cat": CAT_LABELS.get(c, c), "x": x * 1.22, "y": y * 1.22})
    labels = pd.DataFrame(lab_rows)

    dom = [-6.0, 6.0]
    enc_x = alt.X("x:Q", axis=None, scale=alt.Scale(domain=dom))
    enc_y = alt.Y("y:Q", axis=None, scale=alt.Scale(domain=dom))

    ring0 = alt.Chart(grid[grid["anel"] == "z0.0"]).mark_line(
        color="#7a7a76", strokeWidth=1.2, opacity=0.8).encode(
        x=enc_x, y=enc_y, order="ordem:O")
    ring3 = alt.Chart(grid[grid["anel"] == "z3.0"]).mark_line(
        color="#55554f", strokeDash=[4, 4], strokeWidth=1, opacity=0.7).encode(
        x=enc_x, y=enc_y, order="ordem:O")

    layers = [ring3, ring0]
    if reference and reference in profiles:
        ref_df = pd.DataFrame(poly(reference, profiles[reference]))
        layers.append(alt.Chart(ref_df).mark_line(
            color=RADAR_REF, strokeDash=[7, 5], strokeWidth=2, opacity=0.9).encode(
            x=enc_x, y=enc_y, order="ordem:O",
            tooltip=[alt.Tooltip("quem:N", title=""),
                     alt.Tooltip("cat:N", title="categoria"),
                     alt.Tooltip("z:Q", title="z")]))
    if len(df):
        color = alt.Color("quem:N", title="",
                          scale=alt.Scale(domain=list(players), range=RADAR_SERIES),
                          legend=alt.Legend(orient="top", labelLimit=220))
        tt = [alt.Tooltip("quem:N", title=""),
              alt.Tooltip("cat:N", title="categoria"), alt.Tooltip("z:Q", title="z")]
        layers.append(alt.Chart(df).mark_line(strokeWidth=2, opacity=0.9).encode(
            x=enc_x, y=enc_y, color=color, detail="quem:N", order="ordem:O", tooltip=tt))
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
    """Renomeia p/ PT, seleciona/ordena colunas e aplica cor. bar=coluna p/ barra."""
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
    if bar and len(d):                       # df vazio → min()/max() = NaN quebra a barra
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
