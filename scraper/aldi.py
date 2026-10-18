"""Aldi.com.au Weekly Specials price scraper.

Aldi only publishes current Specials online (not a full grocery catalog), so this
returns None for most items most of the time -- that's expected, not a bug. If it
starts returning None for everything including items you know are on special, Aldi
has likely changed its markup -- re-run scripts/capture_fixture.py and update the
selector below.

NOTE: PRICE_SELECTOR here is a best-guess, not yet confirmed against a live-captured
page -- see the same note in scraper/coles.py.
"""
from bs4 import BeautifulSoup

from scraper.base import parse_price_text

SEARCH_URL_TEMPLATE = "https://www.aldi.com.au/en/weekly-specials/?searchTerm={query}"
PRICE_SELECTOR = ".product-tile__price"


def parse_price_from_html(html: str):
    """Extracts the first matching product's price from an Aldi Specials search page.
    Returns a float, or None if no price could be found (including when the item simply
    isn't on special this week)."""
    soup = BeautifulSoup(html, "html.parser")
    price_el = soup.select_one(PRICE_SELECTOR)
    if price_el is None:
        return None
    return parse_price_text(price_el.get_text())


async def fetch_price(page, search_term: str):
    """Navigates `page` (a Playwright page) to the Specials search for `search_term` and
    returns the parsed price, or None on any failure or when nothing is on special. Never
    raises -- callers treat None as 'no current Aldi price' and show that in the UI."""
    try:
        await page.goto(SEARCH_URL_TEMPLATE.format(query=search_term.replace(" ", "+")), timeout=20000)
        await page.wait_for_timeout(2000)
        html = await page.content()
        return parse_price_from_html(html)
    except Exception:
        return None
