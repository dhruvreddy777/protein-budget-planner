import pytest
from fastapi.testclient import TestClient

import storage.db as db_module
import web.app as app_module
from storage.db import insert_price


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_prices.db"
    monkeypatch.setattr(db_module, "DEFAULT_DB_PATH", db_path)
    return TestClient(app_module.app)


def test_index_page_lists_pantry_checkboxes(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "budget" in response.text.lower()
    assert 'name="have_items"' in response.text
    assert "Chicken Breast" in response.text


def test_plan_with_no_price_data_still_shows_pantry_meals(client):
    response = client.post("/plan", data={"budget": "20", "have_items": ["eggs", "cheese", "onion"]})
    assert response.status_code == 200
    assert "run the scraper" in response.text.lower()
    assert "Cheese Omelette" in response.text


def test_plan_with_no_pantry_items_shows_no_pantry_meals_message(client):
    response = client.post("/plan", data={"budget": "20"})
    assert response.status_code == 200
    assert "right now" in response.text.lower()


def test_plan_with_budget_too_low_shows_cheapest_item_hint(client):
    conn = db_module.connect()
    insert_price(conn, "eggs", "coles", 50.00, "2026-01-01T00:00:00")
    response = client.post("/plan", data={"budget": "1"})
    assert response.status_code == 200
    assert "50.00" in response.text


def test_plan_combines_pantry_and_basket_for_shopping_meals(client):
    conn = db_module.connect()
    insert_price(conn, "cheese", "coles", 5.00, "2026-01-01T00:00:00")
    response = client.post("/plan", data={"budget": "20", "have_items": ["eggs", "onion"]})
    assert response.status_code == 200
    assert "Cheese Omelette" in response.text


def test_recipes_page_lists_every_recipe(client):
    response = client.get("/recipes")
    assert response.status_code == 200
    assert "Cheese Omelette" in response.text
    assert response.text.count('class="recipe-card"') == 32


def test_recipe_detail_shows_ingredients_and_steps(client):
    response = client.get("/recipes/cheese_omelette")
    assert response.status_code == 200
    assert "Cooking method" in response.text
    assert "Whisk 3 eggs" in response.text
    assert "Eggs" in response.text


def test_unknown_recipe_returns_404(client):
    assert client.get("/recipes/not_a_recipe").status_code == 404


def test_plan_does_not_put_owned_items_in_basket(client):
    conn = db_module.connect()
    insert_price(conn, "eggs", "coles", 4.00, "2026-01-01T00:00:00")
    insert_price(conn, "cheese", "coles", 5.00, "2026-01-01T00:00:00")
    response = client.post("/plan", data={"budget": "20", "have_items": ["eggs", "onion"]})
    assert response.status_code == 200
    assert "Eggs" not in response.text.split("Your basket")[1].split("Meals you can make after")[0]
    assert "for Cheese Omelette" in response.text
