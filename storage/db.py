"""SQLite-backed price cache."""
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "prices.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    store TEXT NOT NULL,
    price REAL NOT NULL,
    scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_item_store ON prices(item_id, store);
"""


def connect(path: Path = None) -> sqlite3.Connection:
    if path is None:
        path = DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    return conn


def insert_price(conn: sqlite3.Connection, item_id: str, store: str, price: float, scraped_at: str) -> None:
    conn.execute(
        "INSERT INTO prices (item_id, store, price, scraped_at) VALUES (?, ?, ?, ?)",
        (item_id, store, price, scraped_at),
    )
    conn.commit()


def get_latest_prices(conn: sqlite3.Connection) -> dict:
    """Returns {item_id: {store: (price, scraped_at)}} using the most recent row per item/store."""
    rows = conn.execute(
        """
        SELECT item_id, store, price, scraped_at
        FROM prices p
        WHERE scraped_at = (
            SELECT MAX(scraped_at) FROM prices
            WHERE item_id = p.item_id AND store = p.store
        )
        """
    ).fetchall()
    result = {}
    for item_id, store, price, scraped_at in rows:
        result.setdefault(item_id, {})[store] = (price, scraped_at)
    return result


def get_last_scrape_time(conn: sqlite3.Connection):
    row = conn.execute("SELECT MAX(scraped_at) FROM prices").fetchone()
    return row[0] if row else None
