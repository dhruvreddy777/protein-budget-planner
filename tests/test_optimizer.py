from core.models import Item, Recipe
from core.optimizer import build_basket, cheapest_store_for_item, cheapest_single_item_price


def make_item(id, protein_per_100g, unit_grams=500):
    return Item(
        id=id, name=id, category="protein", unit_grams=unit_grams,
        unit_label="unit", protein_per_100g=protein_per_100g,
        coles_search_term=id, aldi_search_term=id,
    )


def test_cheapest_store_for_item_picks_lower_price():
    prices = {"eggs": {"coles": (4.50, "t1"), "aldi": (3.90, "t1")}}
    assert cheapest_store_for_item("eggs", prices) == ("aldi", 3.90)


def test_cheapest_store_for_item_returns_none_when_missing():
    assert cheapest_store_for_item("eggs", {}) is None


def test_build_basket_prefers_high_protein_per_dollar_within_budget():
    items = {
        "chicken": make_item("chicken", protein_per_100g=31, unit_grams=500),  # 155g protein
        "potato": make_item("potato", protein_per_100g=2, unit_grams=2000),    # 40g protein
    }
    prices = {
        "chicken": {"coles": (10.0, "t1")},  # 15.5 g protein per $
        "potato": {"coles": (4.0, "t1")},    # 10 g protein per $
    }
    result = build_basket(items, prices, budget=10.0)
    assert result.item_ids == set(["chicken"])
    assert result.total_spent == 10.0


def test_build_basket_skips_item_that_does_not_fit_but_still_fills_cheaper_one():
    items = {
        "chicken": make_item("chicken", protein_per_100g=31, unit_grams=500),
        "potato": make_item("potato", protein_per_100g=2, unit_grams=2000),
    }
    prices = {
        "chicken": {"coles": (10.0, "t1")},
        "potato": {"coles": (4.0, "t1")},
    }
    result = build_basket(items, prices, budget=8.0)
    assert result.item_ids == set(["potato"])
    assert result.total_spent == 4.0


def test_build_basket_returns_empty_when_nothing_fits():
    items = {"chicken": make_item("chicken", protein_per_100g=31, unit_grams=500)}
    prices = {"chicken": {"coles": (10.0, "t1")}}
    result = build_basket(items, prices, budget=5.0)
    assert result.entries == []
    assert result.total_spent == 0.0


def test_cheapest_single_item_price_returns_minimum():
    items = {"chicken": "ignored", "potato": "ignored"}
    prices = {
        "chicken": {"coles": (10.0, "t1")},
        "potato": {"coles": (4.0, "t1")},
    }
    assert cheapest_single_item_price(items, prices) == 4.0


def test_cheapest_single_item_price_returns_none_when_no_prices():
    assert cheapest_single_item_price({"chicken": "ignored"}, {}) is None


def make_recipe(id, ingredients, protein_per_serving=20, servings=2):
    return Recipe(id=id, name=id, servings=servings, protein_per_serving=protein_per_serving,
                  ingredients=ingredients, method="")


def test_build_basket_never_buys_items_already_owned():
    items = {
        "chicken": make_item("chicken", protein_per_100g=31),
        "potato": make_item("potato", protein_per_100g=2, unit_grams=2000),
    }
    prices = {"chicken": {"coles": (10.0, "t1")}, "potato": {"coles": (4.0, "t1")}}
    result = build_basket(items, prices, budget=20.0, have_ids={"chicken"})
    assert result.item_ids == {"potato"}


def test_build_basket_completes_a_meal_before_topping_up_protein():
    # Pure protein-per-dollar would spend everything on tuna; the meal needs pasta + tomato.
    items = {
        "tuna": make_item("tuna", protein_per_100g=25, unit_grams=1000),   # 250g protein
        "pasta": make_item("pasta", protein_per_100g=13),                 # 65g
        "tomato": make_item("tomato", protein_per_100g=1, unit_grams=400),
    }
    prices = {
        "tuna": {"coles": (5.0, "t1")},
        "pasta": {"coles": (2.0, "t1")},
        "tomato": {"coles": (1.0, "t1")},
    }
    recipes = [make_recipe("tuna_pasta", ["tuna", "pasta", "tomato"])]
    result = build_basket(items, prices, budget=8.0, recipes=recipes)
    assert result.item_ids == {"tuna", "pasta", "tomato"}
    assert all(e.for_recipe == "tuna_pasta" for e in result.entries)


def test_build_basket_uses_pantry_items_to_complete_meals():
    items = {
        "eggs": make_item("eggs", protein_per_100g=13),
        "cheese": make_item("cheese", protein_per_100g=25, unit_grams=250),
        "chicken": make_item("chicken", protein_per_100g=31),
    }
    prices = {
        "eggs": {"coles": (5.0, "t1")},
        "cheese": {"coles": (5.0, "t1")},
        "chicken": {"coles": (5.0, "t1")},  # best protein/$ but not part of any meal
    }
    recipes = [make_recipe("omelette", ["eggs", "cheese"])]
    result = build_basket(items, prices, budget=5.0, have_ids={"eggs"}, recipes=recipes)
    assert result.item_ids == {"cheese"}


def test_build_basket_skips_meal_it_cannot_afford_and_tops_up_instead():
    items = {
        "salmon": make_item("salmon", protein_per_100g=20),
        "rice": make_item("rice", protein_per_100g=7),
        "beans": make_item("beans", protein_per_100g=5),
    }
    prices = {
        "salmon": {"coles": (20.0, "t1")},
        "rice": {"coles": (2.0, "t1")},
        "beans": {"coles": (1.0, "t1")},
    }
    recipes = [make_recipe("salmon_rice", ["salmon", "rice"])]
    result = build_basket(items, prices, budget=5.0, recipes=recipes)
    assert result.item_ids == {"rice", "beans"}
    assert all(e.for_recipe is None for e in result.entries)


def test_build_basket_skips_meal_with_unpriced_ingredient():
    items = {"tofu": make_item("tofu", protein_per_100g=12), "rice": make_item("rice", protein_per_100g=7)}
    prices = {"rice": {"coles": (2.0, "t1")}}
    recipes = [make_recipe("tofu_rice", ["tofu", "rice"])]
    result = build_basket(items, prices, budget=10.0, recipes=recipes)
    assert result.item_ids == {"rice"}
    assert result.entries[0].for_recipe is None


def test_cheapest_single_item_price_ignores_excluded_items():
    items = {"chicken": "ignored", "potato": "ignored"}
    prices = {"chicken": {"coles": (10.0, "t1")}, "potato": {"coles": (4.0, "t1")}}
    assert cheapest_single_item_price(items, prices, exclude={"potato"}) == 10.0


def test_build_basket_handles_meal_completed_as_side_effect_of_another():
    # Buying eggs + cheese for the omelette also completes "cheesy eggs" for free.
    items = {
        "eggs": make_item("eggs", protein_per_100g=13),
        "cheese": make_item("cheese", protein_per_100g=25, unit_grams=250),
        "onion": make_item("onion", protein_per_100g=1),
    }
    prices = {i: {"coles": (2.0, "t1")} for i in items}
    recipes = [
        make_recipe("omelette", ["eggs", "cheese", "onion"], protein_per_serving=40),
        make_recipe("cheesy_eggs", ["eggs", "cheese"], protein_per_serving=10),
    ]
    result = build_basket(items, prices, budget=6.0, recipes=recipes)
    assert result.item_ids == {"eggs", "cheese", "onion"}
