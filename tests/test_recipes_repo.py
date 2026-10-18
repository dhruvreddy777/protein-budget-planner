from core.items_repo import load_items
from core.recipes_repo import load_recipes


def test_load_recipes_returns_expected_count_and_fields():
    recipes = load_recipes()
    assert len(recipes) >= 30
    stir_fry = next(r for r in recipes if r.id == "chicken_rice_stir_fry")
    assert stir_fry.servings == 4
    assert "chicken_breast" in stir_fry.ingredients


def test_all_recipe_ingredients_exist_in_item_catalog():
    items = load_items()
    recipes = load_recipes()
    for recipe in recipes:
        for ingredient_id in recipe.ingredients:
            assert ingredient_id in items, f"{recipe.id} references unknown item {ingredient_id}"


def test_every_recipe_has_steps_and_meal_type():
    for recipe in load_recipes():
        assert recipe.steps, f"{recipe.id} has no cooking steps"
        assert recipe.meal_type in {"breakfast", "lunch", "dinner", "snack"}
        assert recipe.total_minutes > 0
