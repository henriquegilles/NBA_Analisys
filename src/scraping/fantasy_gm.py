"""
Scraper for the "Bandeja de 3" fantasy league on FantasyGM (bskt.fantasygm.com.br).

Unlike the Basketball Reference scrapers, FantasyGM exposes a clean internal JSON
API at ``https://bskt.fantasygm.com.br:82/api``. We only use Selenium to perform
the login (the site is a React SPA and auth is a session key returned as the
``access_token`` cookie); once we have that key we hit the API directly with
``requests`` — much faster and more stable than scraping rendered HTML.

Auth: the API authenticates via a custom ``chavesessao`` header carrying the
session UUID. CORS only blocks browser-origin calls, so server-side ``requests``
work fine. Only ONE session is active per user at a time — running two logins
back to back invalidates the older key, so keep a single login per run.

Credentials are read from the environment, never hard-coded:

    export FGM_EMAIL="you@example.com"
    export FGM_PASS="your-password"
    python fantasy_gm.py

Outputs (written to ``dbt/seeds/`` like the other scrapers):
    fantasy_rosters.csv    — one row per player per franchise (salaries, positions, status)
    fantasy_franchises.csv — franchise directory (24 teams + owners)
    fantasy_standings.csv  — league standings for the current season
"""

import csv
import os
import time
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from common.browser import CHROME_BINARY, CHROMEDRIVER_PATH

BASE = "https://bskt.fantasygm.com.br"
API = "https://bskt.fantasygm.com.br:82/api"

# League / season identifiers (discovered from the API on login).
LIGA = 24          # "Bandeja de 3"
TEMPORADA = 81     # 2026-2027
MY_FRANQUIA = 528  # "Lobos Comunistas" (Henri's team)

SEEDS_DIR = Path(__file__).resolve().parents[2] / "dbt" / "seeds"


def _plain_driver() -> webdriver.Chrome:
    """Headless Chrome WITHOUT selenium-stealth.

    Unlike Basketball Reference, FantasyGM has no bot protection, so we skip the
    stealth patches — they noticeably slow driver startup and were tripping the
    120s webdriver connect timeout on the snap chromedriver.
    """
    opts = Options()
    opts.binary_location = CHROME_BINARY
    for arg in (
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
    ):
        opts.add_argument(arg)
    service = Service(executable_path=CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=opts)


def login() -> str:
    """Log in via headless Chrome and return the session key (chavesessao)."""
    email = os.environ.get("FGM_EMAIL")
    password = os.environ.get("FGM_PASS")
    if not email or not password:
        raise SystemExit("Set FGM_EMAIL and FGM_PASS environment variables first.")

    driver = _plain_driver()
    try:
        driver.get(f"{BASE}/login")
        time.sleep(5)
        driver.find_element(By.CSS_SELECTOR, "input[type=text]").send_keys(email)
        driver.find_element(By.CSS_SELECTOR, "input[type=password]").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        time.sleep(8)
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        sessao = cookies.get("access_token")
        if not sessao:
            raise SystemExit("Login failed — no access_token cookie (check credentials).")
        return sessao
    finally:
        driver.quit()


def api_get(path: str, sessao: str):
    """GET an API path with the session header; return the parsed ``dado`` payload."""
    headers = {
        "chavesessao": sessao,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE}/",
    }
    resp = requests.get(API + path, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("dado")


def get_listao(sessao: str):
    """Fetch /liga/listao/{LIGA} — every franchise with its full roster.

    One call returns all franchises + players + salaries (up to 5 contract years) +
    up to 3 eligible positions + status flags. Reused for rosters, the franchise
    directory, and regenerating the manual seeds, so we fetch it only once.
    """
    return api_get(f"/liga/listao/{LIGA}", sessao)


def scrape_rosters(listao):
    """Return (franchises, roster_rows) built from the listao payload."""
    franchises, roster = [], []
    for fr in listao["detalhes_Franquia"]:
        jogadores = fr.get("jogadores") or []
        franchises.append(
            {
                "codigo_liga": LIGA,
                "codigo_temporada": TEMPORADA,
                "codigo_franquia": fr["codigo"],
                "nome_franquia": fr["nome"],
                "nome_usuario": fr.get("nome_Usuario"),
                "qtd_jogadores": len(jogadores),
            }
        )
        for j in jogadores:
            roster.append(
                {
                    "codigo_liga": LIGA,
                    "codigo_temporada": TEMPORADA,
                    "codigo_franquia": fr["codigo"],
                    "nome_franquia": fr["nome"],
                    "nome_usuario": fr.get("nome_Usuario"),
                    "codigo_jogador": j["codigo"],
                    "codigo_nba": j.get("codigo_NBA"),
                    "nome_jogador": j["nome"],
                    "posicao_1": j.get("posicao_1"),
                    "posicao_2": j.get("posicao_2"),
                    "posicao_3": j.get("posicao_3"),
                    "salario_ano1": j.get("salario_Ano1"),
                    "salario_ano2": j.get("salario_Ano2"),
                    "salario_ano3": j.get("salario_Ano3"),
                    "salario_ano4": j.get("salario_Ano4"),
                    "salario_ano5": j.get("salario_Ano5"),
                    "tipo_salario_1": j.get("tipo_Salario_1"),
                    "tipo_salario_2": j.get("tipo_Salario_2"),
                    "tipo_salario_3": j.get("tipo_Salario_3"),
                    "tipo_salario_4": j.get("tipo_Salario_4"),
                    "tipo_salario_5": j.get("tipo_Salario_5"),
                    "contundido": j.get("contundido"),
                    "restrito": j.get("restrito"),
                    "fora_nba": j.get("fora_NBA"),
                    "draftado": j.get("draftado"),
                }
            )
    return franchises, roster


def scrape_standings(sessao: str):
    """Return standings rows from /franquia/classificacao/{LIGA}/{TEMPORADA}."""
    data = api_get(f"/franquia/classificacao/{LIGA}/{TEMPORADA}", sessao)
    geral = data["classificacao_Geral"]["classificacao_Geral"]
    rows = []
    for r in geral:
        rows.append(
            {
                "codigo_liga": LIGA,
                "codigo_temporada": TEMPORADA,
                "codigo_franquia": r["codigo_Franquia"],
                "nome_franquia": r["nome_Franquia"],
                "posicao": r["posicao"],
                "vitorias": r["quantidade_Vitorias"],
                "derrotas": r["quantidade_Derrotas"],
                "empates": r["quantidade_Empates"],
                "pontos": r["pontos"],
                "sequencia_vitorias": r["sequencia_Vitorias"],
                "saldo_vitorias": r["saldo_Vitorias"],
            }
        )
    return rows


def scrape_draft_class(sessao: str):
    """Return the draft-eligible player pool for the current season.

    /liga/draft/jogador/{LIGA}/{TEMPORADA} — the rich list (position, NBA team,
    rookie-season flag). This is the "current draft class" for prospect scouting.
    """
    data = api_get(f"/liga/draft/jogador/{LIGA}/{TEMPORADA}", sessao) or []
    rows = []
    for p in data:
        rows.append(
            {
                "codigo_liga": LIGA,
                "codigo_temporada": TEMPORADA,
                "codigo_jogador": p["codigo"],
                "codigo_nba": p.get("codigo_NBA"),
                "nome": p["nome"],
                "posicao": p.get("posicao"),
                "posicao_americana": p.get("posicao_Americana"),
                "ano_inicio": p.get("ano_Inicio"),
                "ano_fim": p.get("ano_Fim"),
                "situacao": p.get("situacao"),
                "ativo": p.get("ativo"),
                "franquia_atual_nba": p.get("franquia_Atual"),
                "sigla_franquia_nba": p.get("sigla_Franquia_Atual"),
                "codigo_temporada_calouro": p.get("codigo_Temporada_Calouro"),
                "games_played_flag": p.get("games_Played_Flag"),
                "other_league_experience": p.get("other_League_Experience"),
            }
        )
    return rows


def scrape_draft_picks(sessao: str):
    """Return the draft board (pick order + owning franchise + selection if made).

    /draft/picks/{LIGA}/{TEMPORADA}. Player fields are null until the pick is made.
    """
    data = api_get(f"/draft/picks/{LIGA}/{TEMPORADA}", sessao) or []
    rows = []
    for p in data:
        rows.append(
            {
                "codigo_liga": LIGA,
                "codigo_temporada": TEMPORADA,
                "escolha": p.get("escolha"),
                "codigo_franquia": p.get("codigo_Franquia"),
                "nome_franquia": p.get("nome_Franquia"),
                "codigo_jogador": p.get("codigo_Jogador"),
                "nome_jogador": p.get("nome_Jogador"),
                "escolha_atual": p.get("escolha_Atual"),
            }
        )
    return rows


def scrape_trades(sessao: str):
    """Return one row per traded asset from the league trade history.

    /proposta/historico/{LIGA} returns proposals; each has a ``dados_Proposta`` list
    of assets (players / picks / penalties) moving between two franchises. We flatten
    to one row per asset, carrying the parent proposal's id/date/status.
    """
    data = api_get(f"/proposta/historico/{LIGA}", sessao) or []
    rows = []
    for prop in data:
        for a in prop.get("dados_Proposta") or []:
            rows.append(
                {
                    "codigo_proposta": prop["codigo"],
                    "data_hora": prop.get("data_Hora"),
                    "situacao": prop.get("situacao"),
                    "tipo_ativo": a.get("tipo_Ativo"),
                    "codigo_franquia_envia": a.get("codigo_Franquia_Envia"),
                    "nome_franquia_envia": a.get("nome_Franquia_Envia"),
                    "codigo_franquia_recebe": a.get("codigo_Franquia_Recebe"),
                    "nome_franquia_recebe": a.get("nome_Franquia_Recebe"),
                    "codigo_jogador": a.get("codigo_Jogador"),
                    "nome_jogador": a.get("nome_Jogador"),
                    "valor_jogador": a.get("valor_Jogador"),
                    "tempo_contrato_jogador": a.get("tempo_Contrato_Jogador"),
                    "ano_pick": a.get("ano_Pick"),
                    "rodada_pick": a.get("rodada_Pick"),
                    "swap": a.get("swap"),
                }
            )
    return rows


def scrape_injuries(sessao: str):
    """Return one row per injured player, flattened across franchises.

    /jogador/lesionado/liga/{LIGA} groups injured players by franchise.
    """
    data = api_get(f"/jogador/lesionado/liga/{LIGA}", sessao) or []
    rows = []
    for fr in data:
        for j in fr.get("jogadores") or []:
            rows.append(
                {
                    "codigo_liga": LIGA,
                    "codigo_franquia": fr["codigo_Franquia"],
                    "nome_franquia": fr["nome_Franquia"],
                    "codigo_jogador": j.get("codigo_Jogador"),
                    "nome_jogador": j.get("nome_Jogador"),
                    "posicao_1": j.get("posicao1_Jogador"),
                    "posicao_2": j.get("posicao2_Jogador"),
                    "posicao_3": j.get("posicao3_Jogador"),
                    "time_nba": j.get("nome_Franquia"),
                    "tipo": j.get("tipo"),
                    "situacao": j.get("situacao"),
                    "data": j.get("data"),
                    "data_retorno": j.get("data_Retorno"),
                    "recuperado": j.get("recuperado"),
                }
            )
    return rows


def _salary_cell(value):
    """Format a salary as a plain int string (drop the ``.0``), '' if null."""
    return "" if value is None else str(int(value))


def _positions(player):
    """Join a player's up-to-3 eligible positions with '|' (my_roster format)."""
    pos = [player.get("posicao_1"), player.get("posicao_2"), player.get("posicao_3")]
    return "|".join(p for p in pos if p)


def regenerate_manual_seeds(listao):
    """Rebuild the versioned my_roster.csv and fantasy_contracts.csv from the API.

    These were previously typed by hand for Henri's franchise (Lobos Comunistas).
    We reproduce them exactly so the existing dbt models keep working, but sourced
    from the live roster instead of manual entry:
      - positions  = posicao_1|posicao_2|posicao_3
      - is_rookie  = 1 if the player is ``restrito`` (restricted) else 0
                     (matches the two rookies on the roster; see runbook #27)
      - salary_y1..y3 (the manual schema caps at 3 years; longer deals are rare)
    """
    mine = next(
        (f for f in listao["detalhes_Franquia"] if f["codigo"] == MY_FRANQUIA), None
    )
    if mine is None:
        print(f"  ! franchise {MY_FRANQUIA} not found — manual seeds not regenerated")
        return
    roster, contracts = [], []
    for j in mine.get("jogadores") or []:
        roster.append(
            {
                "player_name": j["nome"],
                "positions": _positions(j),
                "is_rookie": 1 if j.get("restrito") else 0,
            }
        )
        contracts.append(
            {
                "player_name": j["nome"],
                "salary_y1": _salary_cell(j.get("salario_Ano1")),
                "salary_y2": _salary_cell(j.get("salario_Ano2")),
                "salary_y3": _salary_cell(j.get("salario_Ano3")),
            }
        )
    write_csv(roster, "my_roster.csv")
    write_csv(contracts, "fantasy_contracts.csv")


def write_csv(rows, filename):
    """Write a list of dicts to dbt/seeds/<filename>. No-op with a warning if empty."""
    path = SEEDS_DIR / filename
    if not rows:
        print(f"  ! {filename}: no rows, skipped")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {filename}: {len(rows)} rows")


def main():
    print("Logging in to FantasyGM…")
    sessao = login()

    print("Fetching league data…")
    listao = get_listao(sessao)
    franchises, roster = scrape_rosters(listao)
    standings = scrape_standings(sessao)
    draft_class = scrape_draft_class(sessao)
    draft_picks = scrape_draft_picks(sessao)
    trades = scrape_trades(sessao)
    injuries = scrape_injuries(sessao)

    print(f"Writing seeds to {SEEDS_DIR}:")
    write_csv(franchises, "fantasy_franchises.csv")
    write_csv(roster, "fantasy_rosters.csv")
    write_csv(standings, "fantasy_standings.csv")
    write_csv(draft_class, "fantasy_draft_class.csv")
    write_csv(draft_picks, "fantasy_draft_picks.csv")
    write_csv(trades, "fantasy_trades.csv")
    write_csv(injuries, "fantasy_injuries.csv")

    print("Regenerating manual seeds from the live roster:")
    regenerate_manual_seeds(listao)

    # These exist in the API but are empty until the season's schedule is drawn.
    # Once the league generates round 1, wire them the same way (see runbook #27):
    #   /liga/calendario/{LIGA}/{TEMPORADA}      — schedule
    #   /estatistica/confronto/liga/{LIGA}/...   — head-to-head matchups
    #   /leilao/todos/{codigo_Leilao}            — auction
    print("Note: calendar / matchups / auction are empty (season not started yet).")
    print("Done.")


if __name__ == "__main__":
    main()
