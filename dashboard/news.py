"""
NBA news via free RSS (no API key).

Aggregates headlines from public feeds (ESPN/Yahoo/CBS) into a DataFrame. Used by
the dashboard as "context" for fantasy decisions (injuries, trades, role changes).
Shams/Twitter posts would require X's paid API — out of scope here.
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
    """1 row per headline (deduplicated by title), most recent first.

    The fetch uses requests with a PER-REQUEST timeout and hands the bytes to
    feedparser — feedparser.parse(url) exposes no timeout, and touching the
    global socket.setdefaulttimeout races between Streamlit sessions."""
    import requests
    rows = []
    for src, url in FEEDS.items():
        try:
            resp = requests.get(url, timeout=10,
                                headers={"User-Agent": "Mozilla/5.0"})
            parsed = feedparser.parse(resp.content)
        except Exception:
            continue
        for e in parsed.entries:
            rows.append({
                "source": src,
                "title": _clean(e.get("title", "")),
                "published": e.get("published", e.get("updated", "")),
                "_ts": e.get("published_parsed", e.get("updated_parsed", None)),
                "summary": _clean(e.get("summary", ""))[:300],
                "link": e.get("link", ""),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(subset="title")
    df = df.sort_values("_ts", ascending=False, na_position="last")
    return df.drop(columns="_ts").reset_index(drop=True)


def tag_players(df: pd.DataFrame, player_names: list[str]) -> pd.DataFrame:
    """Adds a `players` column = pool names mentioned in the title/summary."""
    if df.empty:
        df["players"] = []
        return df
    names = [n for n in player_names if isinstance(n, str) and len(n) > 3]
    haystack = (df["title"] + " " + df["summary"]).str.lower()
    df["players"] = [
        ", ".join(n for n in names if n.lower() in h) for h in haystack
    ]
    return df
