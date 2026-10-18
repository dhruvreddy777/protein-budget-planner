"""Matches a set of available item IDs against the curated recipe catalog."""


def suggest_meals(recipes: list, available_item_ids: set, top_n: int = 5) -> list:
    """Returns up to top_n recipes whose ingredients are fully covered by
    available_item_ids, ranked by protein_per_serving descending."""
    feasible = [r for r in recipes if r.ingredients and set(r.ingredients).issubset(available_item_ids)]
    feasible.sort(key=lambda r: r.protein_per_serving, reverse=True)
    return feasible[:top_n]
