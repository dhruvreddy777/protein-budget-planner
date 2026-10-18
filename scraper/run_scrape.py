"""Orchestrates scraping all tracked items from Coles and Aldi, writing results to
SQLite. Tolerates partial failure: one item or store failing never aborts the run."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script from the project root

from playwright.async_api import async_playwright

from core.items_repo import load_items
from scraper import coles, aldi
from storage.db import connect, insert_price


async def scrape_all(page, items: dict, conn) -> int:
    """Given an already-open Playwright page (or None, if fetch functions are mocked),
    a loaded items dict, and a DB connection, scrapes each item from both stores and
    writes successful results. Returns the number of price records written."""
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for item in items.values():
        coles_price = await coles.fetch_price(page, item.coles_search_term)
        if coles_price is not None:
            insert_price(conn, item.id, "coles", coles_price, now)
            written += 1

        aldi_price = await aldi.fetch_price(page, item.aldi_search_term)
        if aldi_price is not None:
            insert_price(conn, item.id, "aldi", aldi_price, now)
            written += 1
    return written


async def run() -> int:
    """Entry point: loads items, opens a real browser, scrapes everything, writes to
    the default SQLite DB."""
    items = load_items()
    conn = connect()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        written = await scrape_all(page, items, conn)
        await browser.close()
    return written


if __name__ == "__main__":
    count = asyncio.run(run())
    print(f"Wrote {count} price records.")
