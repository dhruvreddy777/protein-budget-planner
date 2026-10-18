from pathlib import Path

from core.models import Item
from scraper import run_scrape
from storage.db import connect, get_latest_prices


def make_item(id):
    return Item(id=id, name=id, category="protein", unit_grams=500, unit_label="unit",
                protein_per_100g=20, coles_search_term=id, aldi_search_term=id)


async def test_scrape_all_writes_successful_prices_and_skips_failures(monkeypatch):
    items = {"eggs": make_item("eggs"), "milk": make_item("milk")}
    conn = connect(Path(":memory:"))

    async def fake_coles_fetch(page, term):
        return 4.50 if term == "eggs" else None

    async def fake_aldi_fetch(page, term):
        return 3.90

    monkeypatch.setattr(run_scrape.coles, "fetch_price", fake_coles_fetch)
    monkeypatch.setattr(run_scrape.aldi, "fetch_price", fake_aldi_fetch)

    written = await run_scrape.scrape_all(page=None, items=items, conn=conn)

    assert written == 3
    latest = get_latest_prices(conn)
    assert latest["eggs"]["coles"][0] == 4.50
    assert "coles" not in latest.get("milk", {})
    assert latest["milk"]["aldi"][0] == 3.90
