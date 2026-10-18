"""Manual sanity check: scrapes a few real items from Coles and Aldi and prints what it
found. Not run by the automated test suite -- run this yourself whenever you want to
confirm the live scrapers still work against the real sites.

Usage: python scripts/live_check.py
"""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script from the project root

from playwright.async_api import async_playwright

from scraper import aldi, coles

CHECK_ITEMS = ["chicken breast", "eggs", "milk"]


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for term in CHECK_ITEMS:
            coles_price = await coles.fetch_price(page, term)
            aldi_price = await aldi.fetch_price(page, term)
            print(f"{term:20s} coles={coles_price}  aldi={aldi_price}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
