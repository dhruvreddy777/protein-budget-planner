"""Loads the staple grocery item catalog from data/items.yaml."""
from pathlib import Path

import yaml

from core.models import Item

DEFAULT_ITEMS_PATH = Path(__file__).resolve().parent.parent / "data" / "items.yaml"


def load_items(path: Path = None) -> dict:
    """Returns a dict of item_id -> Item."""
    path = path or DEFAULT_ITEMS_PATH
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    items = {}
    for entry in raw["items"]:
        item = Item(
            id=entry["id"],
            name=entry["name"],
            category=entry["category"],
            unit_grams=float(entry["unit_grams"]),
            unit_label=entry["unit_label"],
            protein_per_100g=float(entry["protein_per_100g"]),
            coles_search_term=entry["coles_search_term"],
            aldi_search_term=entry["aldi_search_term"],
        )
        items[item.id] = item
    return items
