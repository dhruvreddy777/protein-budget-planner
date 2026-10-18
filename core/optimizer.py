"""Greedy budget optimizer. Skips items you already have, first buys the missing
ingredients for whole meals (cheapest-to-complete first), then tops up the remaining
budget with the best protein-grams-per-dollar staples, preferring whichever store is
cheaper per item."""
from core.models import BasketEntry, BasketResult


def cheapest_store_for_item(item_id: str, latest_prices: dict):
    """Given {item_id: {store: (price, scraped_at)}}, returns (store, price) for the
    cheapest available store for item_id, or None if no price is available."""
    stores = latest_prices.get(item_id)
    if not stores:
        return None
    best_store, (best_price, _) = min(stores.items(), key=lambda kv: kv[1][0])
    return best_store, best_price


def build_basket(items: dict, latest_prices: dict, budget: float,
                 have_ids=frozenset(), recipes=None) -> BasketResult:
    """items: {item_id: Item}. latest_prices: {item_id: {store: (price, scraped_at)}}.
    have_ids: items already in the pantry, which are never bought. recipes: optional list
    of Recipe to try to complete.

    Phase 1 (only when recipes are given): repeatedly pick the recipe with the most
    recipe protein per dollar of still-missing ingredients that fits the remaining budget,
    and buy those ingredients. Phase 2: greedily fill what's left in descending order of
    protein-per-dollar, skipping any item that would exceed the remaining budget (but
    continuing to consider the rest)."""
    offers = {}  # item_id -> (store, price), for items we could buy
    for item_id in items:
        if item_id in have_ids:
            continue
        cheapest = cheapest_store_for_item(item_id, latest_prices)
        if cheapest is not None and cheapest[1] > 0:
            offers[item_id] = cheapest

    entries = []
    spent = 0.0
    owned = set(have_ids)

    def buy(item_id, for_recipe=None):
        nonlocal spent
        store, price = offers[item_id]
        entries.append(BasketEntry(item=items[item_id], store=store, price=price, for_recipe=for_recipe))
        owned.add(item_id)
        spent += price

    for recipe in _meal_plan(recipes or [], offers, owned, budget):
        for item_id in recipe.ingredients:
            if item_id not in owned:
                buy(item_id, for_recipe=recipe.id)

    candidates = sorted(
        (item_id for item_id in offers if item_id not in owned),
        key=lambda i: items[i].protein_per_unit / offers[i][1], reverse=True,
    )
    for item_id in candidates:
        if spent + offers[item_id][1] <= budget:
            buy(item_id)

    return BasketResult(entries=entries, budget=budget)


def _meal_plan(recipes: list, offers: dict, owned: set, budget: float):
    """Yields recipes to complete, in order. Reads `owned` live, so ingredients bought
    for one recipe make recipes that share them cheaper to complete."""
    remaining = budget
    done = {r.id for r in recipes if set(r.ingredients) <= owned}
    while True:
        best = None
        for recipe in recipes:
            if recipe.id in done or not recipe.ingredients:
                continue
            missing = set(recipe.ingredients) - owned
            if not missing:
                done.add(recipe.id)  # completed for free by an earlier recipe's ingredients
                continue
            if not all(i in offers for i in missing):
                continue  # an ingredient has no price, so the meal can't be completed
            cost = sum(offers[i][1] for i in missing)
            if cost > remaining:
                continue
            score = (recipe.protein_per_serving * recipe.servings / cost, recipe.protein_per_serving)
            if best is None or score > best[0]:
                best = (score, recipe, cost)
        if best is None:
            return
        _, recipe, cost = best
        done.add(recipe.id)
        remaining -= cost
        yield recipe


def cheapest_single_item_price(items: dict, latest_prices: dict, exclude=frozenset()):
    """Returns the lowest available price across all tracked items (except those in
    exclude), or None if none have a price. Used to build a helpful message when the
    budget is too low for any item."""
    prices = []
    for item_id in items:
        if item_id in exclude:
            continue
        cheapest = cheapest_store_for_item(item_id, latest_prices)
        if cheapest:
            prices.append(cheapest[1])
    return min(prices) if prices else None
