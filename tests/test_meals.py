from core.models import Recipe
from core.meals import suggest_meals


def make_recipe(id, ingredients, protein_per_serving):
    return Recipe(id=id, name=id, servings=2, protein_per_serving=protein_per_serving,
                  ingredients=ingredients, method="cook it")


def test_suggest_meals_returns_only_fully_covered_recipes():
    recipes = [
        make_recipe("a", ["chicken", "rice"], 30),
        make_recipe("b", ["beef", "pasta"], 25),
    ]
    result = suggest_meals(recipes, available_item_ids=set(["chicken", "rice", "onion"]))
    assert [r.id for r in result] == ["a"]


def test_suggest_meals_ranks_by_protein_descending():
    recipes = [
        make_recipe("low", ["eggs"], 10),
        make_recipe("high", ["eggs"], 30),
    ]
    result = suggest_meals(recipes, available_item_ids=set(["eggs"]))
    assert [r.id for r in result] == ["high", "low"]


def test_suggest_meals_respects_top_n():
    recipes = [make_recipe(str(i), ["eggs"], i) for i in range(10)]
    result = suggest_meals(recipes, available_item_ids=set(["eggs"]), top_n=3)
    assert len(result) == 3


def test_suggest_meals_returns_empty_when_nothing_fits():
    recipes = [make_recipe("a", ["chicken"], 30)]
    result = suggest_meals(recipes, available_item_ids=set(["onion"]))
    assert result == []


def test_suggest_meals_returns_empty_for_empty_item_set():
    recipes = [make_recipe("a", ["chicken"], 30)]
    result = suggest_meals(recipes, available_item_ids=set())
    assert result == []
