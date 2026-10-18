from pathlib import Path

from storage.db import connect, insert_price, get_latest_prices, get_last_scrape_time


def test_insert_and_get_latest_prices_returns_most_recent_per_store():
    conn = connect(Path(":memory:"))
    insert_price(conn, "eggs", "coles", 4.50, "2026-01-01T10:00:00")
    insert_price(conn, "eggs", "coles", 4.20, "2026-01-02T10:00:00")
    insert_price(conn, "eggs", "aldi", 3.90, "2026-01-02T09:00:00")

    latest = get_latest_prices(conn)

    assert latest["eggs"]["coles"] == (4.20, "2026-01-02T10:00:00")
    assert latest["eggs"]["aldi"] == (3.90, "2026-01-02T09:00:00")


def test_get_last_scrape_time_returns_none_when_empty():
    conn = connect(Path(":memory:"))
    assert get_last_scrape_time(conn) is None


def test_get_last_scrape_time_returns_max_timestamp():
    conn = connect(Path(":memory:"))
    insert_price(conn, "eggs", "coles", 4.50, "2026-01-01T10:00:00")
    insert_price(conn, "milk", "aldi", 2.10, "2026-01-03T08:00:00")
    assert get_last_scrape_time(conn) == "2026-01-03T08:00:00"
