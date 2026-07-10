"""
FA/Draft 2.0 — camada de decisão avançada sobre o `fantasy_engine`.

Implementa o adendo:
  (g) PESOS VINDOS DA SIMULAÇÃO — H2H winrate sim → Δwinrate por +1σ por categoria.
  (e) POOL DE FA REAL — jogadores valorados não rosterados nas 24 franquias.
  (f) VALOR SOBRE REPOSIÇÃO POSICIONAL — z acima do replacement level da posição.
  (h) CONCORRÊNCIA RIVAL — cap dos rivais × fraqueza por categoria → urgência.
  (i) WAIVER WATCH — franquias acima do limite de roster → cortes prováveis.
  (j) DESCONTO DE LESÃO — fantasy_injuries aplica desconto na projeção.
  (k) CACHE — persiste saídas em dashboard/data_cache/.

Nota de dados: players_stats só tem 2025-26 e NÃO tem plus/minus → simulação usa 6 cats
(PTS/REB/AST/STOCKS/3PM/TOV), maioria = 4 de 6. Roster do Lobos reflete o último scrape
(pré-trocas); re-rodar `fantasy_gm.py` p/ o pós-Mitchell.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

from fantasy_engine import Engine, CATS, MY_FRANCHISE, norm, _f

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")
os.makedirs(CACHE, exist_ok=True)
POS_GROUPS = {"PG": "G", "SG": "G", "SF": "W", "PF": "B", "C": "B"}


def _cache(df: pd.DataFrame, name: str) -> pd.DataFrame:
    df.to_csv(os.path.join(CACHE, name), index=False)
    return df


class FADraft:
    def __init__(self, eng: Engine | None = None, my_team: str = MY_FRANCHISE):
        self.eng = eng or Engine()
        self.my = my_team
        self._injuries = self._load_injuries()

    # ---------- matriz de categoria por time (top-10 titulares) ----------
    def team_cat_matrix(self) -> pd.DataFrame:
        ls = self.eng.league_strength().set_index("Franquia")
        return ls[CATS]

    # ---------- (g) simulação de pesos por categoria ----------
    def simulate_weights(self, bump: float = 1.0) -> dict:
        """Δwinrate por +bump(σ) em cada categoria p/ o MEU time.
        H2H: ganho a categoria se meu total > total do adversário; ganho o confronto
        se levo >= 4 de 6 categorias. Peso = quanto +1σ numa cat sobe meu winrate."""
        M = self.team_cat_matrix()
        if self.my not in M.index:
            raise ValueError(f"{self.my} não está na matriz")
        me = M.loc[self.my].copy()
        opps = M.drop(index=self.my)

        def winrate(vec) -> float:
            wins = 0
            for _, opp in opps.iterrows():
                cats_won = sum(1 for c in CATS if vec[c] > opp[c])
                wins += (cats_won >= 4)  # maioria de 6
            return wins / len(opps)

        base = winrate(me)
        weights = {}
        for c in CATS:
            bumped = me.copy(); bumped[c] += bump
            weights[c] = round(winrate(bumped) - base, 4)
        out = pd.DataFrame({"categoria": CATS,
                            "peso_dwinrate": [weights[c] for c in CATS]}).sort_values(
                            "peso_dwinrate", ascending=False)
        out.attrs["base_winrate"] = base
        _cache(out, "sim_weights.csv")
        self.weights = weights
        self.base_winrate = base
        return weights

    # ---------- (e) pool de FA real ----------
    def fa_pool(self) -> pd.DataFrame:
        rostered = set(self.eng.rosters["key"])
        banned = getattr(self.eng, "banned", set())
        val = self.eng.val.reset_index()
        pool = val[~val["key"].isin(rostered) & ~val["key"].isin(banned)].copy()
        # só rotação (pool de referência): G>=25, MP>=18 já filtrado no fit; mantém quem tem VA
        pool = pool.dropna(subset=["VA"])
        pool["pos_group"] = pool["Pos"].str.split("-").str[0].map(POS_GROUPS).fillna("W")
        return pool

    # ---------- (f) replacement level por posição ----------
    def replacement_levels(self, pool: pd.DataFrame | None = None) -> dict:
        pool = pool if pool is not None else self.fa_pool()
        rep = {}
        for pg, g in pool.groupby("pos_group"):
            # replacement = ~melhor FA disponível na posição (top-3 média p/ suavizar)
            rep[pg] = round(g.nlargest(3, "VA")["VA"].mean(), 2)
        return rep

    # ---------- (g+f+j) board de FA ponderado ----------
    def fa_board(self, top: int = 30) -> pd.DataFrame:
        if not hasattr(self, "weights"):
            self.simulate_weights()
        pool = self.fa_pool()
        rep = self.replacement_levels(pool)
        # normaliza os pesos da simulação p/ somarem 1 (escala comparável ao z) —
        # só cats com Δwinrate > 0 importam; PTS/STOCKS (Δ=0) saem do fit.
        pos_w = {c: max(self.weights[c], 0) for c in CATS}
        tot = sum(pos_w.values()) or 1.0
        w = {c: pos_w[c] / tot for c in CATS}
        # fit_sim = média ponderada do z do jogador nas cats que movem meu winrate
        zc = {c: f"z_{c}" for c in CATS}
        pool["fit_sim"] = sum(pool[zc[c]] * w[c] for c in CATS)
        # (f) valor sobre reposição: VA menos o replacement da posição dele
        pool["va_over_repl"] = pool["VA"] - pool["pos_group"].map(rep)
        # (j) desconto de lesão
        pool["injury_disc"] = pool["key"].map(self._injuries).fillna(1.0)
        # blend 50/50 (documentado): valor sobre reposição × fit ponderado por winrate
        pool["score"] = (0.5 * pool["va_over_repl"] + 0.5 * pool["fit_sim"]) * pool["injury_disc"]
        cols = ["Player", "Pos", "pos_group", "Age", "VA", "va_over_repl", "fit_sim",
                "injury_disc", "score"]
        board = (pool[cols].rename(columns={"Player": "Jogador"})
                 .sort_values("score", ascending=False).head(top).round(2))
        return _cache(board, "fa_board.csv")

    # ---------- (h) concorrência rival ----------
    def rival_competition(self) -> pd.DataFrame:
        """Rivais com cap livre E fracos numa categoria disputam FAs daquela cat."""
        cap = self.eng.team_cap().set_index("Franquia")["Espaço_M"]
        M = self.team_cat_matrix()
        league_mean = M.mean()
        rows = []
        for fr in M.index:
            if fr == self.my:
                continue
            space = cap.get(fr, 0)
            weak = [c for c in CATS if M.loc[fr, c] < league_mean[c] - 3]  # bem abaixo da média
            rows.append({"Franquia": fr, "cap_livre_M": round(space, 1),
                         "categorias_fracas": ", ".join(weak) or "—",
                         "ameaca_FA": round(max(space, 0) / 40 * len(weak), 2)})
        out = pd.DataFrame(rows).sort_values("ameaca_FA", ascending=False)
        return _cache(out, "rival_competition.csv")

    # ---------- (i) waiver watch ----------
    def waiver_watch(self) -> pd.DataFrame:
        """Franquias acima do limite de roster cortarão o pior jogador = FA de graça."""
        fr = self.eng._csv("fantasy_franchises.csv")
        limit = 15  # limite típico de elenco (ajustável)
        rv = self.eng._roster_with_value()
        rows = []
        for name, g in rv.groupby("nome_franquia"):
            n = len(g)
            if n > limit:
                worst = g.dropna(subset=["VA"]).nsmallest(n - limit, "VA")
                for _, p in worst.iterrows():
                    rows.append({"Franquia": name, "corte_provavel": p["nome_jogador"],
                                 "VA": round(p["VA"], 2)})
        out = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Franquia", "corte_provavel", "VA"])
        return _cache(out, "waiver_watch.csv")

    # ==================== DRAFT BOARD 2.0 ====================

    # ---------- (a) curva de pick (produção esperada por slot) ----------
    def pick_curve(self, min_year: int = 2016) -> pd.DataFrame:
        """Produção fantasy média por número de pick (proxy: pg_pts+trb+ast do draft.csv,
        classes >= min_year). Suavizada por LOESS-ish (média móvel). Persistida."""
        d = self.eng._csv("draft.csv")
        d = d[d["draft_year"].map(_f) >= min_year].copy()
        d["fantasy_proxy"] = d["pg_pts"].map(_f) + d["pg_trb"].map(_f) + d["pg_ast"].map(_f)
        d["pick"] = d["pick"].map(_f)
        curve = d.dropna(subset=["pick", "fantasy_proxy"]).groupby("pick")["fantasy_proxy"].mean()
        # média móvel de 5 picks p/ suavizar ruído
        smooth = curve.reindex(range(1, 61)).interpolate().rolling(5, center=True, min_periods=1).mean()
        out = smooth.reset_index(); out.columns = ["pick", "expected_prod"]
        return _cache(out.round(2), "pick_curve.csv")

    # ---------- (d) preço real de pick (minerado dos trades) ----------
    def pick_price(self) -> pd.DataFrame:
        """Preço médio de uma pick por rodada — soma do valor dos jogadores no OUTRO lado
        das propostas que envolveram pick (ano_pick/rodada_pick preenchidos)."""
        t = self.eng._csv("fantasy_trades.csv")
        props_with_pick = t[t["rodada_pick"].map(_f) > 0]["codigo_proposta"].unique()
        rows = []
        for pid in props_with_pick:
            grp = t[t["codigo_proposta"] == pid]
            picks = grp[grp["rodada_pick"].map(_f) > 0]
            players_val = grp[grp["valor_jogador"].map(_f) > 0]["valor_jogador"].map(_f).sum() / 1e6
            for _, pk in picks.iterrows():
                rows.append({"rodada": int(_f(pk["rodada_pick"])), "preco_M": round(players_val, 1)})
        if not rows:
            return pd.DataFrame(columns=["rodada", "preco_medio_M", "n"])
        df = pd.DataFrame(rows)
        agg = df.groupby("rodada")["preco_M"].agg(["mean", "count"]).reset_index()
        agg.columns = ["rodada", "preco_medio_M", "n"]
        return _cache(agg.round(1), "pick_price.csv")

    # ---------- (b) vácuo de minutos por time NBA × posição ----------
    def _minutes_occupied(self) -> dict:
        s = self.eng.stats
        s = s.copy()
        s["pos_group"] = s["Pos"].astype(str).str.split("-").str[0].map(POS_GROUPS).fillna("W")
        s["mp"] = s["MP"].map(_f).fillna(0)
        occ = s.groupby(["Team", "pos_group"])["mp"].sum().to_dict()
        return occ

    # ---------- (a)+(b)+(c) board de draft ----------
    def draft_board2(self, top: int = 30) -> pd.DataFrame:
        dc = self.eng._csv("fantasy_draft_class.csv")
        dc["key"] = dc["nome"].map(norm)
        dc["pos_group"] = dc["posicao"].astype(str).str.split("-").str[0].map(POS_GROUPS).fillna("W")
        # market pick# do draft NBA 2026 real (sinal de talento)
        d26 = self.eng._csv("draft.csv")
        d26 = d26[d26["draft_year"].map(_f) == 2026].copy()
        d26["key"] = d26["player_name"].map(norm)
        pick_of = dict(zip(d26["key"], d26["pick"].map(_f)))
        # curva
        curve = self.pick_curve().set_index("pick")["expected_prod"].to_dict()
        # landing spot (final) + oportunidade curada
        try:
            land = self.eng.landing.set_index("prospect_key")
            opp_mult = land["opportunity_mult"].to_dict()
            team_final = land["nba_team_final"].to_dict()
        except Exception:
            opp_mult, team_final = {}, {}
        occ = self._minutes_occupied()
        # NBA team abbr do prospecto (draft-night no seed; usa como fallback)
        team_abbr = dict(zip(dc["key"], dc["sigla_franquia_nba"].astype(str)))

        rows = []
        for _, p in dc.iterrows():
            k = p["key"]; pk = pick_of.get(k)
            # (a) projeção pela curva do pick real (fallback: mediana ~pick 30)
            proj = curve.get(round(pk), curve.get(30, 5.0)) if pk else curve.get(30, 5.0)
            # (b) vácuo de minutos no time × posição (menos ocupado = mais oportunidade)
            occ_min = occ.get((team_abbr.get(k, "?"), p["pos_group"]), 240)
            vacuum = max(0.0, (48 * 5 * 0.55) - occ_min) / (48 * 5)  # 0..1 aprox
            mult = opp_mult.get(k, 1.0)
            # score = projeção × oportunidade (curada) × (1 + vácuo de minutos)
            score = proj * mult * (1 + 0.5 * vacuum)
            rows.append({
                "Prospecto": p["nome"], "Pos": p["posicao"],
                "pick_NBA": int(pk) if pk else None,
                "proj_curva": round(proj, 1),
                "opp_mult": round(mult, 2),
                "vacuo_min": round(vacuum, 2),
                "time_final": team_final.get(k, "?"),
                "score": round(score, 1),
            })
        board = pd.DataFrame(rows).sort_values("score", ascending=False).head(top)
        return _cache(board, "draft_board2.csv")

    # ---------- (c)+(d) vale COMPRAR uma pick? (surplus vs preço real) ----------
    def pick_buy_analysis(self) -> pd.DataFrame:
        """Cruza produção esperada por slot (curva) com o preço real de pick (trades).
        Rookie custa ~$5M/3 anos → surplus = valor de produção − custo de cap.
        Decide se vale dar $34M(1ª)/$14M(2ª) em jogadores pra COMPRAR a pick."""
        curve = self.pick_curve().set_index("pick")["expected_prod"]
        price = self.pick_price().set_index("rodada")["preco_medio_M"].to_dict()
        rows = []
        for slot in [1, 3, 5, 10, 15, 20, 30, 45]:
            rnd = 1 if slot <= 30 else 2
            prod = curve.get(slot, np.nan)
            cost = price.get(rnd, np.nan)
            # produção "vale" ~ prod (em pts+reb+ast) ; rookie custa ~$5M de cap (barato)
            rows.append({
                "pick": slot, "rodada": rnd,
                "prod_esperada": round(prod, 1),
                "custo_pick_M": cost,                     # preço em jogadores p/ comprar
                "salario_rookie_M": 5.0 if rnd == 1 else 2.5,
                "vale_comprar": "SIM" if (prod >= 14 and rnd == 1) or (prod >= 9 and rnd == 2)
                                else "só se barato",
            })
        return _cache(pd.DataFrame(rows), "pick_buy_analysis.csv")

    # ---------- lê tudo e persiste (para o app/relatório) ----------
    def build_all(self):
        self.simulate_weights(); self.fa_board(); self.rival_competition()
        self.waiver_watch(); self.pick_curve(); self.pick_price()
        self.draft_board2(); self.pick_buy_analysis()
        return sorted(os.listdir(CACHE))

    # ---------- (j) lesões ----------
    def _load_injuries(self) -> dict:
        try:
            inj = self.eng._csv("fantasy_injuries.csv")
        except FileNotFoundError:
            return {}
        disc = {}
        for _, r in inj.iterrows():
            k = norm(r.get("nome_jogador", ""))
            sit = str(r.get("situacao", "")).lower()
            # desconto: dia-a-dia -0.05, semanas -0.20, temporada -0.60
            if "temporada" in sit or "season" in sit:
                disc[k] = 0.4
            elif "semana" in sit or "week" in sit:
                disc[k] = 0.8
            else:
                disc[k] = 0.95
        return disc
