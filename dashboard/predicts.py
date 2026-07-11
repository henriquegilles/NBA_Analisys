"""
Predicts v2 (Rodada 6, Fase 1) — consolida as métricas preditivas por jogador
num artefato reproduzível (antes viviam em scripts ad-hoc no /tmp, perdidos).

Por jogador do elenco (ou de qualquer franquia):
  - VA 2025-26 (punt-TOV, do Engine) + z por categoria
  - Floor / Ceiling / Risco(CV)      — gamelogs jogo-a-jogo (doc 01 §2.3)
  - Sensibilidade a minutos @24/28/32 — rates por minuto re-projetados no pool
  - Minutes Upside                    — VA@32 − VA@MP atual
  - Usage Upside                      — TS% alto + USG% baixo = posse escondida
  - Aging curve                       — multiplicador por idade (corte 2025-26,
                                        sanity-check por experiência no draft.csv)
  - Development                       — VA − (idade−27)·0.35 (doc 01 §2.3)
  - Dynasty                           — média do VA projetado nos próximos 3 anos
  - Contexto 2026-27                  — role_mult do seed nba_context_overrides
  - VA projetado 2026-27              — VA(minutos ajustados) × aging × contexto
  - flag_amostra                      — G<25 = ruído (não confiar no z)

Uso:
    from fantasy_engine import Engine
    from predicts import Predicts
    p = Predicts(Engine())
    p.roster_predicts()          # DataFrame do meu elenco (grava data_cache/predicts_v2.csv)
    p.aging_curve()              # curva idade -> multiplicador
    python predicts.py           # smoke: tabela + 4 casos de validação direcional
"""
from __future__ import annotations
import os

import numpy as np
import pandas as pd

from fantasy_engine import Engine, CATS, MY_FRANCHISE, norm, _f

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")

# Categorias que valem ponto no punt-TOV (TOV ignorada por decisão de build).
# VALUE_CATS entra no VA/sensibilidade a minutos (inclui PM — runbook #34);
# SCORE_CATS é só contagem (floor/ceiling/CV): PM é signed e com ele o score
# por jogo cruzaria o zero, desestabilizando o CV (desvio/média).
VALUE_CATS = ["PTS", "REB", "AST", "STOCKS", "3PM", "PM"]
SCORE_CATS = ["PTS", "REB", "AST", "STOCKS", "3PM"]
GAMELOG_COLS = {"PTS": "PTS", "REB": "TRB", "AST": "AST", "3PM": "three_p", "PM": "pm"}
MIN_GAMES_TRUST = 25          # abaixo disso, z-score é ruído (flag_amostra)
DEV_SLOPE = 0.35              # Development = VA − (idade−27)·0.35 (doc 01 §2.3)
PEAK_AGES = (26, 27, 28)      # pico da aging curve (normalizador)


class Predicts:
    def __init__(self, eng: Engine | None = None):
        self.eng = eng or Engine()
        self._gl = None
        self._adv = None
        self._curve = None

    # ---------- fontes ----------
    def _gamelogs(self) -> pd.DataFrame:
        if self._gl is None:
            gl = pd.read_csv(os.path.join(self.eng.seeds, "player_gamelogs.csv"),
                             low_memory=False)
            gl["key"] = gl["player_name"].map(norm)
            for c in ["PTS", "TRB", "AST", "STL", "BLK", "three_p", "TOV"]:
                gl[c] = gl[c].map(_f)
            gl["STOCKS"] = gl["STL"] + gl["BLK"]
            # pré-computa o que é independente de jogador — sem isso cada
            # jogador paga um std() de coluna inteira + um scan dos 26k jogos
            self._gl_std = {c: gl[GAMELOG_COLS.get(c, c)].std(ddof=0) or 1.0
                            for c in SCORE_CATS}
            self._gl_by_key = dict(tuple(gl.groupby("key")))
            self._gl = gl
        return self._gl

    def _advanced(self) -> pd.DataFrame:
        if self._adv is None:
            adv = pd.read_csv(os.path.join(self.eng.seeds, "players_advanced_stats.csv"))
            adv["key"] = adv["Player"].map(norm)
            adv = adv.sort_values("G", key=lambda s: s.map(_f), ascending=False)
            self._adv = adv.drop_duplicates("key", keep="first").set_index("key")
        return self._adv

    # ---------- aging curve ----------
    # Curva PARAMÉTRICA (pico 26-28, declínio >30 acelerando). Por que não 100%
    # empírica: o corte 2025-26 sofre de sobrevivência (aos 33+ só os bons seguem
    # na liga → mediana por idade NÃO cai; ver aging_curve_empirical), e o
    # draft.csv só tem agregados de carreira (sem pares idade×temporada). Os dois
    # servem de sanity-check da FORMA: a rampa jovem (~0.90 aos 21-22) bate com a
    # curva por anos-de-liga do draft.csv (mediana exp-2 ≈ 0.90×pico exp-8), e o
    # declínio pós-30 vem da literatura delta-method (Fase 4 pode recalibrar).
    AGING = {19: 0.85, 20: 0.88, 21: 0.91, 22: 0.94, 23: 0.96, 24: 0.98,
             25: 0.99, 26: 1.00, 27: 1.00, 28: 1.00, 29: 0.99, 30: 0.97,
             31: 0.95, 32: 0.92, 33: 0.89, 34: 0.85, 35: 0.81, 36: 0.77,
             37: 0.73, 38: 0.69, 39: 0.65, 40: 0.61, 41: 0.57}

    def aging_curve(self) -> pd.Series:
        if self._curve is None:
            self._curve = pd.Series(self.AGING, name="mult").rename_axis("Age")
        return self._curve

    def aging_curve_empirical(self) -> pd.Series:
        """Mediana (suavizada) do score de produção por idade no corte 2025-26,
        normalizada pelo pico 26-28. NÃO usada na projeção — evidência da
        limitação do corte transversal (sobrevivência achata o declínio)."""
        s = self.eng.stats
        pool = s[(s["G"].map(_f) >= MIN_GAMES_TRUST) & (s["MP"].map(_f) >= 18)].copy()
        pool["Age"] = pool["Age"].map(_f)
        cv = self.eng._cat_vector(pool)
        prod = sum(cv[c] / (cv[c].std(ddof=0) or 1.0) for c in SCORE_CATS)
        pool = pool.assign(prod=prod.values)
        med = pool.groupby(pool["Age"].astype(int))["prod"].median()
        med = med.rolling(3, center=True, min_periods=1).mean()
        peak = med.loc[[a for a in PEAK_AGES if a in med.index]].max()
        return (med / peak).round(3)

    def _age_mult(self, age: float, years_ahead: int = 1) -> float:
        """curve(age+k)/curve(age), clipado — passo de envelhecimento."""
        if pd.isna(age):
            return 1.0
        c = self.aging_curve()
        lo, hi = c.index.min(), c.index.max()
        a0 = int(np.clip(age, lo, hi))
        a1 = int(np.clip(age + years_ahead, lo, hi))
        return float(np.clip(c.loc[a1] / c.loc[a0], 0.75, 1.15))

    def validate_aging_on_draft(self) -> pd.DataFrame:
        """Sanity-check da forma da curva com o draft.csv (longitudinal por coorte):
        produção de carreira (pg_pts+pg_trb+pg_ast) por anos-desde-o-draft.
        Não é idade×temporada (draft.csv só tem agregados de carreira), mas mostra
        rampa até a janela ~5-9 anos de liga (idade ~24-28) e queda depois."""
        d = pd.read_csv(os.path.join(self.eng.seeds, "draft.csv"))
        d = d[d["career_games"].map(_f) >= 100].copy()
        d["exp"] = 2026 - d["draft_year"].map(_f)
        d["prod"] = d["pg_pts"].map(_f) + d["pg_trb"].map(_f) + d["pg_ast"].map(_f)
        out = (d[(d["exp"] >= 1) & (d["exp"] <= 20)]
               .groupby(d["exp"].astype(int))["prod"].agg(["median", "count"]))
        return out.rename(columns={"median": "prod_mediana", "count": "n"})

    # ---------- métricas por jogo (gamelogs) ----------
    def _pergame_scores(self, key: str) -> pd.Series | None:
        """Fantasy-score punt-TOV por jogo: soma de stat/σ_pool nas 5 categorias
        que valem ponto (sem centrar na média → score positivo, CV estável)."""
        self._gamelogs()
        g = self._gl_by_key.get(key)
        if g is None or len(g) < 5:
            return None
        score = sum(g[GAMELOG_COLS.get(c, c)] / self._gl_std[c] for c in SCORE_CATS)
        return score.dropna()

    # ---------- sensibilidade a minutos ----------
    def _va_at_minutes(self, row: pd.Series, minutes: float) -> float:
        """VA punt-TOV se o jogador jogar `minutes`/jogo: rate por minuto ×
        minutos-alvo, re-padronizado contra o pool per-game da temporada.
        Aproximação linear (rate constante) — superestima levemente em saltos
        grandes de minutos (rotações longas cansam), por isso os cenários param em 32."""
        mp = _f(row["MP"])
        if not mp or mp <= 0:
            return np.nan
        va = 0.0
        for c in VALUE_CATS:
            z_c = row[f"z_{c}"]
            mean_c, std_c = self._pool_mean_std[c]
            pg = z_c * std_c + mean_c            # média por jogo implícita no z
            proj = pg / mp * minutes
            va += (proj - mean_c) / std_c
        return va

    @staticmethod
    def _apply_mult(va: float, mult: float) -> float:
        """Multiplicador de desconto/bônus SEGURO PARA SINAL. VA é centrado em ~0
        e fica negativo — `va * 0.15` num VA -2 diria que perder a temporada
        MELHORA um jogador ruim (-2 → -0.3). Regra: desconto num VA negativo
        empurra pra BAIXO na mesma proporção (va * (2 - mult))."""
        if pd.isna(va) or pd.isna(mult):
            return np.nan
        return va * mult if va >= 0 else va * (2.0 - mult)

    def _project_va(self, v: pd.Series, mp: float, role_mult: float,
                    ctx, aging: float) -> float:
        """VA projetado 2026-27. Dois regimes (change_type validado no Engine):
        - lesão: role_mult é DISPONIBILIDADE (fração da temporada) → desconta o
          VA no nível de minutos atual. Butler 0.15 ⇒ valor de temporada ≈ 0,
          sem inventar um jogador de 5 min/jogo.
        - troca/papel: role_mult ajusta MINUTOS por jogo (banco↓/titular↑) e o
          VA é recalculado nesse nível."""
        if not mp or pd.isna(mp):
            return np.nan
        change = str(ctx["change_type"]) if ctx is not None else ""
        if change == "injury":
            return self._apply_mult(
                self._apply_mult(self._va_at_minutes(v, mp), role_mult), aging)
        proj_min = float(np.clip(mp * role_mult, 8, 36))
        return self._apply_mult(self._va_at_minutes(v, proj_min), aging)

    @property
    def _pool_mean_std(self):
        # DES-normalização de z usa o MESMO pool do Engine._build_value — se o
        # piso do pool mudar lá, o z inverte contra o pool certo aqui.
        if not hasattr(self, "_pms"):
            self._pms = {c: (self.eng.pool_mean[c], self.eng.pool_std[c] or 1.0)
                         for c in VALUE_CATS}
        return self._pms

    # ---------- consolidação ----------
    def roster_predicts(self, franchise: str = MY_FRANCHISE) -> pd.DataFrame:
        eng = self.eng
        r = eng.rosters[eng.rosters["nome_franquia"] == franchise]
        adv = self._advanced()
        usg_med = adv["usg_pct"].map(_f).median()   # invariantes do loop
        ts_med = adv["ts_pct"].map(_f).median()
        rows = []
        for _, rr in r.iterrows():
            key = rr["key"]
            if key not in eng.val.index:
                rows.append({"Jogador": rr["nome_jogador"], "Pos": rr["posicao_1"],
                             "flag_amostra": "sem stats NBA (calouro?)"})
                continue
            v = eng.val.loc[key]
            age, g, mp = _f(v["Age"]), _f(v["G"]), _f(v["MP"])
            va = float(v["VA"])          # definição única de VA mora no Engine

            sc = self._pergame_scores(key)
            floor = float(np.percentile(sc, 20)) if sc is not None else np.nan
            ceil = float(np.percentile(sc, 85)) if sc is not None else np.nan
            cv = float(sc.std(ddof=0) / sc.mean()) if sc is not None and sc.mean() > 0 else np.nan

            va24, va28, va32 = (self._va_at_minutes(v, m) for m in (24, 28, 32))
            va_now_m = self._va_at_minutes(v, mp)
            min_up = va32 - va_now_m if not pd.isna(va32) else np.nan

            usg = _f(adv.loc[key, "usg_pct"]) if key in adv.index else np.nan
            ts = _f(adv.loc[key, "ts_pct"]) if key in adv.index else np.nan
            usage_up = (max(0.0, (ts - ts_med) * 10) if not pd.isna(ts) and not pd.isna(usg)
                        and usg < usg_med else 0.0)

            ctx = eng.context.loc[key] if key in eng.context.index else None
            role_mult = _f(ctx["role_mult"]) if ctx is not None else 1.0
            role_note = str(ctx["role_2026_27"]) if ctx is not None else ""

            aging = self._age_mult(age, 1)
            dev = va - (age - 27) * DEV_SLOPE if not pd.isna(age) else np.nan
            va_proj = self._project_va(v, mp, role_mult, ctx, aging)
            # dynasty: média do VA projetado em t+1..t+3 — _age_mult(age+1, k) já é
            # a razão cumulativa curve(age+1+k)/curve(age+1); papel = o do ano 1
            dyn = np.nan
            if not pd.isna(va_proj):
                dyn = float(np.mean([self._apply_mult(va_proj, self._age_mult(age + 1, k))
                                     for k in range(3)]))

            rows.append({
                "Jogador": v["Player"], "Pos": v["Pos"], "Age": age, "G": g, "MP": mp,
                "VA_2526": round(va, 2), "Floor": round(floor, 1), "Ceiling": round(ceil, 1),
                "CV": round(cv, 2) if not pd.isna(cv) else np.nan,
                "VA@24": round(va24, 2), "VA@28": round(va28, 2), "VA@32": round(va32, 2),
                "MinutesUpside": round(min_up, 2) if not pd.isna(min_up) else np.nan,
                "UsageUpside": round(usage_up, 2),
                "aging_mult": round(aging, 3), "Development": round(dev, 2),
                "role_mult": role_mult, "contexto_2627": role_note,
                "VA_proj_2627": round(va_proj, 2) if not pd.isna(va_proj) else np.nan,
                "Dynasty": round(dyn, 2) if not pd.isna(dyn) else np.nan,
                "flag_amostra": "⚠️ G<25 = ruído" if g and g < MIN_GAMES_TRUST else "",
            })
        df = pd.DataFrame(rows).sort_values("VA_proj_2627", ascending=False, na_position="last")
        if franchise == MY_FRANCHISE:   # o artefato persistido é o MEU elenco;
            os.makedirs(CACHE, exist_ok=True)   # predicts de rival não o sobrescrevem
            df.to_csv(os.path.join(CACHE, "predicts_v2.csv"), index=False)
        return df

    # ---------- validação direcional (brief da Rodada 6) ----------
    def validation_cases(self) -> pd.DataFrame:
        """4 casos com direção conhecida: Butler≈0 (LCA), Vučević↓ (banco),
        Claxton↑ (~+1, titular), Ware↑ (rebuild)."""
        cases = ["Jimmy Butler", "Nikola Vučević", "Nic Claxton", "Kel'el Ware"]
        out = []
        for name in cases:
            key = norm(name)
            if key not in self.eng.val.index:
                continue
            v = self.eng.val.loc[key]
            va = float(v["VA"])
            ctx = self.eng.context.loc[key] if key in self.eng.context.index else None
            role_mult = _f(ctx["role_mult"]) if ctx is not None else 1.0
            mp = _f(v["MP"])
            va_proj = self._project_va(v, mp, role_mult, ctx,
                                       self._age_mult(_f(v["Age"]), 1))
            out.append({"Jogador": v["Player"], "VA_2526": round(va, 2),
                        "role_mult": role_mult,
                        "VA_proj_2627": round(va_proj, 2),
                        "delta": round(va_proj - va, 2)})
        return pd.DataFrame(out)


if __name__ == "__main__":
    p = Predicts()
    print("=== Predicts v2 — Lobos Comunistas ===")
    print(p.roster_predicts().to_string(index=False))
    print("\n=== Casos de validação direcional ===")
    print(p.validation_cases().to_string(index=False))
    print("\n=== Aging curve paramétrica (idade -> mult) ===")
    print(p.aging_curve().round(3).to_string())
    print("\n=== Aging curve empírica 2025-26 (só evidência; sobrevivência) ===")
    print(p.aging_curve_empirical().to_string())
    print("\n=== Sanity-check draft.csv (produção × anos de liga) ===")
    print(p.validate_aging_on_draft().to_string())
