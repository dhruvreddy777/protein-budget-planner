"""Coles.com.au price scraper.

Coles' site is a JS-rendered app, so prices are fetched with a real headless browser
(Playwright). If parse_price_from_html starts returning None for everything, Coles has
likely changed its markup -- re-run scripts/capture_fixture.py for a fresh sample and
update the selector below.

NOTE: PRICE_SELECTOR here is a best-guess based on Coles' typical markup pattern as of
this writing, NOT yet confirmed against a live-captured page (capture_fixture.py needs
a real browser to run, which wasn't available while this file was first written).
Before relying on this scraper, run scripts/capture_fixture.py for a real "chicken
breast" search, inspect the result, and update PRICE_SELECTOR if it doesn't match.
"""
from bs4 import BeautifulSoup

from scraper.base import parse_price_text

SEARCH_URL_TEMPLATE = "https://www.coles.com.au/search?q={query}"
PRICE_SELECTOR = '[data-testid="product-pricing"] .price__value'


def parse_price_from_html(html: str):
    """Extracts the first product's price from a Coles search results page.
    Returns a float, or None if no price could be found."""
    soup = BeautifulSoup(html, "html.parser")
    price_el = soup.select_one(PRICE_SELECTOR)
    if price_el is None:
        return None
    return parse_price_text(price_el.get_text())


async def fetch_price(page, search_term: str):
    """Navigates `page` (a Playwright page) to the search results for `search_term` and
    returns the parsed price, or None on any failure. Never raises -- callers treat None
    as 'could not get a price this time' and fall back to cached data."""
    try:
        await page.goto(SEARCH_URL_TEMPLATE.format(query=search_term.replace(" ", "+")), timeout=20000)
        await page.wait_for_selector(PRICE_SELECTOR, timeout=10000)
        html = await page.content()
        return parse_price_from_html(html)
    except Exception:
        return None
