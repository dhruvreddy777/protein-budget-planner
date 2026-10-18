import csv

from core.items_repo import load_items
from sample_data.load_sample_data import SAMPLE_CSV


def test_sample_csv_rows_reference_known_items_and_valid_stores():
    items = load_items()
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 50
    for row in rows:
        assert row["item_id"] in items, f"unknown item_id {row['item_id']}"
        assert row["store"] in ("coles", "aldi")
        assert float(row["price"]) > 0


def test_tofu_has_no_aldi_row_demonstrating_coles_only_case():
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tofu_stores = set(row["store"] for row in rows if row["item_id"] == "tofu")
    assert tofu_stores == set(["coles"])
