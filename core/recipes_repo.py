"""Loads the curated high-protein recipe catalog from data/recipes.json."""
import json
from pathlib import Path

from core.models import Recipe

DEFAULT_RECIPES_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes.json"


def load_recipes(path: Path = None) -> list:
    """Returns a list of Recipe."""
    path = path or DEFAULT_RECIPES_PATH
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [
        Recipe(
            id=entry["id"],
            name=entry["name"],
            servings=int(entry["servings"]),
            protein_per_serving=float(entry["protein_per_serving"]),
            ingredients=list(entry["ingredients"]),
            method=entry["method"],
            emoji=entry.get("emoji", "🍽️"),
            meal_type=entry.get("meal_type", "dinner"),
            prep_minutes=int(entry.get("prep_minutes", 0)),
            cook_minutes=int(entry.get("cook_minutes", 0)),
            steps=tuple(entry.get("steps", ())),
            tip=entry.get("tip", ""),
        )
        for entry in raw["recipes"]
    ]
