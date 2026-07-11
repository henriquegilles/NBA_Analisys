"""
Motor de métricas fantasy (Bandeja de 3) — versão reproduzível dos scripts pandas
que na sessão de decisão viviam ad-hoc em /tmp. Lê os seeds direto (não precisa do DB),
o que torna o protótipo portátil.

Responsabilidades:
  - carregar seeds (rosters da liga, stats NBA, gamelogs, draft class, landing spots)
  - z-score por categoria sobre pool de rotação (7-cat, TOV invertido)
  - VA punt-TOV = z_total - z_tov (métrica central)
  - per-36, floor/ceiling, consistência (gamelogs)
  - pool de FA, força de liga por categoria, cap, board de draft ajustado por oportunidade

Uso:
    from fantasy_engine import Engine
    eng = Engine()               # carrega tudo dos seeds
    eng.my_roster()              # DataFrame do meu time (Lobos)
    eng.fa_targets()             # alvos de FA ranqueados
    eng.draft_board()            # board de draft por oportunidade
    eng.league_strength()        # 24 times x categoria
    eng.team_cap()               # cap por franquia
"""
from __future__ import annotations
import os
import re
import unicodedata as ud

import numpy as np
import pandas as pd

SEEDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seeds")
MY_FRANCHISE = "Lobos Comunistas"
CAP = 190.0
# As 7 categorias REAIS da liga (vence quem leva 4+ das 7; TOV é o nosso punt).
# PM (+/-) vem dos GAMELOGS — o per-game da BBR (players_stats) não traz +/-,
# e por isso o motor jogou com 6 cats até a Rodada 6 (corrigido: runbook #34).
CATS = ["PTS", "REB", "AST", "STOCKS", "3PM", "PM", "TOV"]
WIN_CATS = 4          # confronto: leva quem vence 4+ das 7 (doc 06 §3)


def norm(s: str) -> str:
    """Normaliza nome p/ join. Igual à macro dbt norm_name: sem acento, minúsculo,
    remove TODO não-alfanumérico (espaços/pontuação) — resolve acento (Dončić) E
    alinha com as chaves dos seeds (dariusacuffjr)."""
    s = ud.normalize("NFKD", str(s))
    s = "".join(c for c in s if not ud.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


class Engine:
    def __init__(self, seeds_dir: str = SEEDS):
        self.seeds = seeds_dir
        self._load()
        self._build_value()

    # ---------- carga ----------
    def _csv(self, name):
        return pd.read_csv(os.path.join(self.seeds, name))

    def _load(self):
        self.stats = self._csv("players_stats.csv")          # per-game 2025-26
        self.rosters = self._csv("fantasy_rosters.csv")
        self.draft = self._csv("fantasy_draft_class.csv")
        try:
            self.landing = self._csv("nba_landing_spots.csv")
        except FileNotFoundError:
            self.landing = pd.DataFrame(columns=["prospect_key", "nba_team_final", "opportunity_mult"])
        self.stats["key"] = self.stats["Player"].map(norm)
        # dedup: jogadores trocados têm >1 linha (TOT + times) -> fan-out no merge/cap.
        # Mantém a de mais jogos por jogador (1 valoração por pessoa).
        self.stats = (self.stats.sort_values("G", key=lambda s: s.map(_f), ascending=False)
                      .drop_duplicates("key", keep="first").reset_index(drop=True))
        self._merge_plus_minus()
        self.rosters["key"] = self.rosters["nome_jogador"].map(norm)
        self.rosters = self.rosters.drop_duplicates(["nome_franquia", "key"], keep="first")
        self._apply_trade_overrides()
        self._apply_nba_context_overrides()
        self._load_banned()
        self._load_restricted()

    def _merge_plus_minus(self):
        """+/- por jogo a partir dos GAMELOGS (a tabela per-game da BBR não traz
        +/-). Média de plus_minus por jogo do jogador (todas as equipes da
        temporada), coerção tolerante — o campo vem como string ('+5'/'-3') e
        pode ter lixo de header repetido. Vira a coluna PM_pg em self.stats."""
        try:
            gl = pd.read_csv(os.path.join(self.seeds, "player_gamelogs.csv"),
                             usecols=["player_name", "plus_minus", "team",
                                      "game_date", "game_result"], low_memory=False)
        except (FileNotFoundError, ValueError):
            self.stats["PM_pg"] = np.nan
            self.team_margin = {}
            return
        gl["pm"] = gl["plus_minus"].map(_f)
        gl["key"] = gl["player_name"].map(norm)
        pm = gl.groupby("key")["pm"].mean()
        self.stats["PM_pg"] = self.stats["key"].map(pm)
        # saldo médio do TIME por jogo ("W, 128-110" → +18), p/ ajustar o PM de
        # quem TROCOU de time (ver _apply_nba_context_overrides / doc 09 §17.3)
        tg = gl.dropna(subset=["game_result"]).drop_duplicates(["team", "game_date"]).copy()
        sc = tg["game_result"].str.extract(r"(\d+)-(\d+)")
        margin = sc[0].map(_f) - sc[1].map(_f)
        self.team_margin = margin.groupby(tg["team"].values).mean().to_dict()
        # saldo do time DE ORIGEM por JOGADOR (média dos times em que ele de fato
        # jogou): resolve o 'nba_team_old=2TM' do seed (Vučević), que não existe
        # em team_margin e silenciosamente zeraria o ajuste
        gl["_tmargin"] = gl["team"].map(self.team_margin)
        self.player_old_margin = gl.groupby("key")["_tmargin"].mean().to_dict()

    # regimes conhecidos do seed de contexto; typo ('Injury') falha ALTO no load,
    # não silenciosamente na projeção (o regime muda a semântica do role_mult)
    CONTEXT_CHANGE_TYPES = {"trade", "fa-signing", "waived", "injury", "re-sign"}
    CONTEXT_STATS_SEASON = "2025-26"   # o seed corrige ESTE snapshot; quando o
    # scrape 2026-27 nascer com os times certos, o override deixa de casar sozinho

    def _apply_nba_context_overrides(self):
        """Aplica o contexto NBA de julho/2026 sobre as stats 2025-26 (que trazem o
        time da temporada passada). Seed versionado `nba_context_overrides.csv`
        (player_name, nba_team_new, change_type, role_2026_27, role_mult, source):
        corrige o `Team` do jogador afetado (ocupação de minutos, contexto) e guarda
        o papel 2026-27 + multiplicador p/ os predicts."""
        try:
            ov = self._csv("nba_context_overrides.csv")
        except FileNotFoundError:
            self.context = pd.DataFrame(
                columns=["key", "nba_team_new", "change_type",
                         "role_2026_27", "role_mult", "source"])
            return
        ov = ov[ov["player_name"].notna()].copy()
        bad = set(ov["change_type"].dropna()) - self.CONTEXT_CHANGE_TYPES
        if bad:
            raise ValueError(f"nba_context_overrides.csv: change_type desconhecido "
                             f"{bad} — regimes válidos: {self.CONTEXT_CHANGE_TYPES}")
        ov["key"] = ov["player_name"].map(norm)
        # jogador com 2 linhas (trocado E depois lesionado): vale a mais RECENTE
        ov = (ov.sort_values("date_confirmed")
                .drop_duplicates("key", keep="last"))
        team_map = dict(zip(ov["key"], ov["nba_team_new"]))
        known = set(self.stats["Team"].dropna()) | {"FA"}
        unknown = set(team_map.values()) - known
        if unknown:
            raise ValueError(f"nba_context_overrides.csv: time(s) fora do padrão "
                             f"BBR: {unknown} (typo? use os códigos de players_stats)")
        mask = (self.stats["key"].isin(team_map)
                & (self.stats.get("season", self.CONTEXT_STATS_SEASON)
                   == self.CONTEXT_STATS_SEASON))
        # ajuste de +/- por MUDANÇA DE TIME (Melhoria A da Fase 4, doc 09 §17.3):
        # o PM_pg carrega o time antigo — quem saiu de time ruim é punido na
        # categoria errada (Claxton/BKN). Desloca METADE do delta de saldo médio
        # entre times (shrinkage 0.5 = heurística; o papel do jogador também muda).
        tm = getattr(self, "team_margin", {})
        pom = getattr(self, "player_old_margin", {})
        if tm:
            # origem = saldo dos times onde o jogador JOGOU (cobre '2TM');
            # destino sem saldo (waivado → 'FA') = sem ajuste, PM antigo fica
            adj = self.stats.loc[mask, "key"].map(
                lambda k: 0.5 * (tm.get(team_map.get(k), np.nan)
                                 - pom.get(k, np.nan)))
            self.stats.loc[mask, "PM_pg"] = (
                self.stats.loc[mask, "PM_pg"] + adj.fillna(0.0))
        self.stats.loc[mask, "Team"] = self.stats.loc[mask, "key"].map(team_map)
        self.context = ov.set_index("key", drop=False)

    def _load_banned(self):
        """Jogadores BANIDOS da liga (não podem ser rostered/alvo). Seed versionado
        `fantasy_banned_players.csv`. Vira um set de chaves normalizadas p/ filtrar do
        pool de FA e de qualquer lista de alvos. Vazio se o seed não existir."""
        try:
            b = self._csv("fantasy_banned_players.csv")
            self.banned = set(b["player_name"].dropna().map(norm))
        except FileNotFoundError:
            self.banned = set()

    def _load_restricted(self):
        """Jogadores RESTRITOS na FA (cada franquia protege 1 expiring $0 — o holder
        retém/iguala, então não são alvo). Seed versionado `fantasy_restricted_players.csv`.
        Diferente dos banidos, continuam contando na força da liga (seguem rostered);
        só saem das listas de alvos. Vazio se o seed não existir."""
        try:
            r = self._csv("fantasy_restricted_players.csv")
            self.restricted = set(r["player_name"].dropna().map(norm))
        except FileNotFoundError:
            self.restricted = set()

    def _apply_trade_overrides(self):
        """Aplica trades JÁ FECHADAS sobre o snapshot do scrape (que pode ser pré-troca).
        Seed versionado `fantasy_trade_overrides.csv` (player_name, to_franchise): reatribui
        o jogador (com o contrato dele) à nova franquia. Picks não são linha de roster → ignoradas.
        Reprodutível e sem re-scrape; some sozinho quando um scrape novo já refletir a troca."""
        try:
            ov = self._csv("fantasy_trade_overrides.csv")
        except FileNotFoundError:
            return
        ov = ov[ov["player_name"].notna() & (ov["player_name"].astype(str).str.strip() != "")]
        if ov.empty:
            return
        dest = dict(zip(ov["player_name"].map(norm), ov["to_franchise"]))
        mask = self.rosters["key"].isin(dest)
        self.rosters.loc[mask, "nome_franquia"] = self.rosters.loc[mask, "key"].map(dest)

    # ---------- valoração 7-cat ----------
    def _cat_vector(self, df):
        return pd.DataFrame({
            "PTS": df["PTS"].map(_f), "REB": df["TRB"].map(_f), "AST": df["AST"].map(_f),
            "STOCKS": df["STL"].map(_f) + df["BLK"].map(_f),
            "3PM": df["three_p"].map(_f), "PM": df["PM_pg"].map(_f),
            "TOV": -df["TOV"].map(_f),
        })

    # piso do pool de referência (z-scores) — fonte única; predicts/fa_draft leem daqui
    POOL_MIN_GAMES = 25
    POOL_MIN_MP = 18.0

    def reference_pool(self) -> pd.DataFrame:
        s = self.stats
        return s[(s["G"].map(_f) >= self.POOL_MIN_GAMES)
                 & (s["MP"].map(_f) >= self.POOL_MIN_MP)]

    def _build_value(self):
        s = self.stats
        pool = self.reference_pool()
        cv_pool = self._cat_vector(pool)
        # fillna: sem gamelogs (scrape antigo) o PM do pool inteiro seria NaN e
        # replace(0,1) não pega NaN → z_PM NaN em massa degradaria tudo em silêncio
        mean = cv_pool.mean().fillna(0)
        std = cv_pool.std(ddof=0).replace(0, 1).fillna(1)
        # expostos p/ quem precisa DES-normalizar z (predicts: sensibilidade a minutos)
        self.pool_mean, self.pool_std = mean, std
        cv = self._cat_vector(s)
        z = (cv - mean) / std
        z.columns = [f"z_{c}" for c in CATS]
        val = s[["Player", "key", "Pos", "Age", "MP", "G", "three_pa", "three_p_pct", "ft_pct"]].copy()
        val = pd.concat([val, z], axis=1)
        val["z_total"] = z.sum(axis=1)
        val["VA"] = val["z_total"] - val["z_TOV"]          # punt-TOV (inclui PM)
        # fit ponderado p/ Lobos (AST+3PM 1.5x; PM peso normal). z_PM NaN (jogador
        # sem gamelog) vira 0 = mesma semântica do skipna do z_total — senão o
        # fit propaga NaN e o jogador some de fa_targets/fa_board sem aviso
        val["fit"] = (z["z_PTS"] + z["z_REB"] + z["z_STOCKS"] + z["z_PM"].fillna(0)
                      + 1.5 * z["z_AST"] + 1.5 * z["z_3PM"])
        self.val = val.set_index("key")

    # ---------- helpers de roster ----------
    def _roster_with_value(self, franchise=None):
        r = self.rosters if franchise is None else self.rosters[self.rosters["nome_franquia"] == franchise]
        j = r.merge(self.val, left_on="key", right_index=True, how="left", suffixes=("", "_v"))
        j["salary_y1_m"] = j["salario_ano1"].map(_f).fillna(0) / 1e6
        return j

    # ---------- superfícies públicas ----------
    def my_roster(self):
        j = self._roster_with_value(MY_FRANCHISE)
        cols = ["nome_jogador", "posicao_1", "Age", "salary_y1_m", "VA",
                "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV"]
        return (j[cols].rename(columns={"nome_jogador": "Jogador", "posicao_1": "Pos"})
                .sort_values("VA", ascending=False))

    def fa_targets(self, top=30):
        paid = set(self.rosters[self.rosters["salario_ano1"].map(_f).fillna(0) > 0]["key"])
        fa_bound = self.rosters[self.rosters["salario_ano1"].map(_f).fillna(0) == 0][["key", "nome_franquia"]]
        holder = dict(zip(fa_bound["key"], fa_bound["nome_franquia"]))
        s = self.stats
        pool = s[(s["G"].map(_f) >= 25) & (s["MP"].map(_f) >= 18)]["key"]
        # jogadores $0 são "FA-bound" (matcháveis), mas os do MEU time não são alvo — já são meus
        mine_keys = set(self.rosters[self.rosters["nome_franquia"] == MY_FRANCHISE]["key"])
        avail = [k for k in pool if k not in paid and k not in self.banned
                 and k not in self.restricted and k not in mine_keys]
        v = self.val.loc[[k for k in avail if k in self.val.index]].copy()
        v["held_by"] = [holder.get(k, "(livre)") for k in v.index]
        _pg = {"PG": "Armador", "SG": "Armador", "SF": "Ala", "PF": "Ala-pivô", "C": "Pivô"}
        v["Grupo"] = v["Pos"].str.split("-").str[0].map(_pg).fillna("Ala")
        cols = ["Player", "Pos", "Grupo", "Age", "VA", "fit",
                "z_PTS", "z_REB", "z_AST", "z_STOCKS", "z_3PM", "z_PM", "z_TOV", "held_by"]
        return v[cols].rename(columns={"Player": "Jogador"}).sort_values("fit", ascending=False).head(top)

    def draft_board(self, top=25):
        d = self.draft.copy()
        d["key"] = d["nome"].map(norm)
        land = self.landing.set_index("prospect_key")["opportunity_mult"].to_dict() if len(self.landing) else {}
        team = self.landing.set_index("prospect_key")["nba_team_final"].to_dict() if len(self.landing) else {}
        # projeção viria do fct_prospect_scouting (DB). Sem DB, usa proxy do college se houver.
        d["opp_mult"] = d["key"].map(land).fillna(1.0)
        d["nba_team"] = d["key"].map(team).fillna("?")
        cols = ["nome", "posicao", "posicao_americana", "nba_team", "opp_mult"]
        return (d[cols].rename(columns={"nome": "Prospecto", "posicao": "Pos"})
                .sort_values("opp_mult", ascending=False).head(top))

    def league_strength(self):
        rows = []
        for fr, g in self._roster_with_value().groupby("nome_franquia"):
            top = g.dropna(subset=["VA"]).nlargest(10, "VA")
            rows.append({"Franquia": fr, **{c: round(top[f"z_{c}"].sum(), 1) for c in CATS},
                         "Total_VA": round(top["VA"].sum(), 1)})
        df = pd.DataFrame(rows).sort_values("Total_VA", ascending=False).reset_index(drop=True)
        df.insert(0, "Rank", df.index + 1)
        return df

    def team_cap(self):
        r = self._roster_with_value()
        agg = r.groupby("nome_franquia")["salary_y1_m"].sum().round(1)
        df = agg.reset_index().rename(columns={"nome_franquia": "Franquia", "salary_y1_m": "Folha_M"})
        df["Espaço_M"] = (CAP - df["Folha_M"]).round(1)
        return df.sort_values("Espaço_M", ascending=False).reset_index(drop=True)
