from scraper.base import parse_price_text


def test_parse_simple_dollar_price():
    assert parse_price_text("$8.50") == 8.50


def test_parse_price_with_trailing_text():
    assert parse_price_text("$12.00 each") == 12.00


def test_parse_plain_number():
    assert parse_price_text("8.5") == 8.5


def test_parse_price_with_thousands_comma():
    assert parse_price_text("$1,234.50") == 1234.50


def test_parse_returns_none_for_no_digits():
    assert parse_price_text("Out of stock") is None


def test_parse_returns_none_for_empty_string():
    assert parse_price_text("") is None
