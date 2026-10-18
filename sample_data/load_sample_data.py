"""Loads the illustrative sample_prices.csv into the real SQLite price cache, so you can
see the app working end-to-end without installing Playwright or scraping live sites
first. These are made-up, illustrative prices for demo purposes only -- NOT real current
prices. Run the real scraper (scraper/run_scrape.py) to get actual current prices.

Usage: python sample_data/load_sample_data.py
"""
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script from the project root

from storage.db import connect, insert_price

SAMPLE_CSV = Path(__file__).resolve().parent / "sample_prices.csv"


def main() -> None:
    conn = connect()
    count = 0
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            insert_price(conn, row["item_id"], row["store"], float(row["price"]), row["scraped_at"])
            count += 1
    print(f"Loaded {count} sample price records into prices.db")


if __name__ == "__main__":
    main()
