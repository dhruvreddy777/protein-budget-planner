"""One-off helper: fetches a live page with Playwright and saves its HTML to a fixture
file, so scraper parsers can be developed and tested against a real, frozen sample.

Usage:
    python scripts/capture_fixture.py coles "chicken breast" tests/fixtures/coles_chicken_breast.html
    python scripts/capture_fixture.py aldi "chicken breast" tests/fixtures/aldi_chicken_breast.html
"""
import asyncio
import sys

from playwright.async_api import async_playwright

URLS = {
    "coles": "https://www.coles.com.au/search?q={query}",
    "aldi": "https://www.aldi.com.au/en/weekly-specials/?searchTerm={query}",
}


async def capture(store: str, query: str, out_path: str) -> None:
    url = URLS[store].format(query=query.replace(" ", "+"))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)  # let client-side rendering settle
        html = await page.content()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        await browser.close()
    print(f"Saved {store} page for {query} to {out_path}")


if __name__ == "__main__":
    store_arg, query_arg, out_path_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    asyncio.run(capture(store_arg, query_arg, out_path_arg))
