"""
Shared HTML parsing utilities for Basketball Reference scrapers.

BBR wraps its main statistical tables inside HTML comments to prevent
easy scraping. The uncomment_tables() function strips those comments so
BeautifulSoup can parse the tables normally.
"""

from bs4 import BeautifulSoup, Comment


def uncomment_tables(soup: BeautifulSoup) -> BeautifulSoup:
    """
    BBR hides data tables inside HTML comments like:
        <!-- <table id="...">...</table> -->

    This function finds every Comment node and replaces it with the
    parsed HTML it contains, making the tables visible to bs4.

    Note: we use c.replace_with(...) rather than soup.append(...)
    because in BeautifulSoup 4.13 append() returns a list and
    indexing into it raises an IndexError when the list is empty.
    """
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        inner = BeautifulSoup(str(c), "lxml")
        if inner.find("table"):
            c.replace_with(inner)
    return soup


def get_table(soup: BeautifulSoup, table_id: str):
    """Return the <table> tag with *table_id*, or raise ValueError."""
    table = soup.find("table", {"id": table_id})
    if table is None:
        raise ValueError(
            f"Table #{table_id} not found in page. BBR may have changed its HTML."
        )
    return table
