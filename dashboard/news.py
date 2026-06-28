"""
Notícias da NBA via RSS grátis (sem chave de API).

Agrega manchetes de feeds públicos (ESPN/Yahoo/CBS) num DataFrame. Usado pelo
painel como "contexto" pra decisões de fantasy (lesões, trocas, mudança de role).
Para tweets do Shams/Twitter seria preciso a API paga do X — fora de escopo aqui.
"""

import re
import pandas as pd
import feedparser

FEEDS = {
    "ESPN": "https://www.espn.com/espn/rss/nba/news",
    "Yahoo": "https://sports.yahoo.com/nba/rss/",
    "CBS": "https://www.cbssports.com/rss/headlines/nba/",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def get_nba_news() -> pd.DataFrame:
    """1 linha por manchete (deduplicada por título), mais recente primeiro."""
    rows = []
    for src, url in FEEDS.items():
        try:
            parsed = feedparser.parse(url)
        except Exception:
            continue
        for e in parsed.entries:
            rows.append({
                "fonte": src,
                "titulo": _clean(e.get("title", "")),
                "publicado": e.get("published", e.get("updated", "")),
                "_ts": e.get("published_parsed", e.get("updated_parsed", None)),
                "resumo": _clean(e.get("summary", ""))[:300],
                "link": e.get("link", ""),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(subset="titulo")
    df = df.sort_values("_ts", ascending=False, na_position="last")
    return df.drop(columns="_ts").reset_index(drop=True)


def tag_players(df: pd.DataFrame, player_names: list[str]) -> pd.DataFrame:
    """Adiciona coluna `jogadores` = nomes do pool citados no título/resumo."""
    if df.empty:
        df["jogadores"] = []
        return df
    names = [n for n in player_names if isinstance(n, str) and len(n) > 3]
    haystack = (df["titulo"] + " " + df["resumo"]).str.lower()
    df["jogadores"] = [
        ", ".join(n for n in names if n.lower() in h) for h in haystack
    ]
    return df
