from pathlib import Path

from scraper.coles import parse_price_from_html

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "coles_chicken_breast.html"
EXPECTED_PRICE = 8.00  # matches the placeholder fixture; update after a real capture


def test_parse_price_from_real_fixture():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    assert parse_price_from_html(html) == EXPECTED_PRICE


def test_parse_price_from_html_returns_none_for_empty_page():
    assert parse_price_from_html("<html><body>no products</body></html>") is None
