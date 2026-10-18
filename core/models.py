"""Core data models shared across the app."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    category: str
    unit_grams: float
    unit_label: str
    protein_per_100g: float
    coles_search_term: str
    aldi_search_term: str

    @property
    def protein_per_unit(self) -> float:
        """Grams of protein in one purchasable unit (one pack/bag/etc.)."""
        return self.protein_per_100g * (self.unit_grams / 100.0)


@dataclass(frozen=True)
class PriceRecord:
    item_id: str
    store: str
    price: float
    scraped_at: str  # ISO 8601 timestamp


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    servings: int
    protein_per_serving: float
    ingredients: list
    method: str
    emoji: str = "🍽️"
    meal_type: str = "dinner"
    prep_minutes: int = 0
    cook_minutes: int = 0
    steps: tuple = ()
    tip: str = ""

    @property
    def total_minutes(self) -> int:
        return self.prep_minutes + self.cook_minutes

    @property
    def protein_total(self) -> float:
        return self.protein_per_serving * self.servings


@dataclass
class BasketEntry:
    item: Item
    store: str
    price: float
    for_recipe: str = None  # id of the recipe this item was bought to complete, if any

    @property
    def protein_total(self) -> float:
        return self.item.protein_per_unit


@dataclass
class BasketResult:
    entries: list
    budget: float

    @property
    def total_spent(self) -> float:
        return round(sum(e.price for e in self.entries), 2)

    @property
    def total_protein(self) -> float:
        return round(sum(e.protein_total for e in self.entries), 1)

    @property
    def item_ids(self):
        return {e.item.id for e in self.entries}
