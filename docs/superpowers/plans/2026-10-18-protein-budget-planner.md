# ProteinBudget Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python web app that, given a grocery budget and/or a list of items you already have at home, finds the cheapest basket of staple groceries across Coles and Aldi (Sydney) and suggests high-protein meals you can make — both from what you already own and from what buying the basket would unlock. Includes a pandas/Jupyter analysis layer on the same data, as a Data Science portfolio piece.

**Architecture:** A single FastAPI process (`run.py`) serves a plain HTML/JS form (budget + a checklist of items you already have) and a results page. A Playwright-based scraper populates a local SQLite price cache on demand. A greedy optimizer picks the cheapest basket; a meal matcher ranks curated recipes against item sets (pantry items, and pantry + basket combined). A separate pandas/Jupyter notebook reads the same SQLite file for exploratory analysis. See `docs/superpowers/specs/2026-10-18-protein-budget-planner-design.md` for the full design rationale.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, Playwright (Chromium), BeautifulSoup4, SQLite (stdlib `sqlite3`), PyYAML, pandas, matplotlib, nbformat, pytest + pytest-asyncio.

**A note on the scraper tasks (8 and 9):** Coles' and Aldi's real HTML markup can't be known in advance — it has to be captured from the live site and inspected before a parser can be written against it. Those two tasks include an explicit "capture and inspect" step for exactly this reason; every other task in this plan is fully specified up front.

**A note on git:** `git` commands were intermittently blocked by an environment/tooling issue during planning. If `git commit` fails when you reach a commit step, skip it, keep working, and do one batch commit covering everything once git is working again — don't let it block implementation progress.

---

## Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `core/__init__.py`, `storage/__init__.py`, `scraper/__init__.py`, `web/__init__.py`, `sample_data/__init__.py`, `notebook/__init__.py` (all empty)

- [ ] **Step 1: Create the directory structure**

Run (from `C:\Users\dhruv\Documents\projects\protein-budget-planner`):
```bash
mkdir -p core storage scraper web/templates web/static sample_data notebook tests/fixtures scripts data
```

- [ ] **Step 2: Write `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.6
jinja2==3.1.4
python-multipart==0.0.9
playwright==1.47.0
beautifulsoup4==4.12.3
PyYAML==6.0.2
pandas==2.2.2
matplotlib==3.9.2
nbformat==5.10.4
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 3: Write `.gitignore`**

```
venv/
__pycache__/
*.pyc
prices.db
.pytest_cache/
.ipynb_checkpoints/
```

- [ ] **Step 4: Write `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
```

- [ ] **Step 5: Create empty `__init__.py` files**

Create empty files at: `core/__init__.py`, `storage/__init__.py`, `scraper/__init__.py`, `web/__init__.py`, `sample_data/__init__.py`, `notebook/__init__.py`.

- [ ] **Step 6: Create a virtual environment and install dependencies**

```bash
python -m venv venv
```
Activate it (Windows): `venv\Scripts\activate` — then:
```bash
pip install -r requirements.txt
```

- [ ] **Step 7: Install the Playwright browser**

```bash
playwright install chromium
```

- [ ] **Step 8: Verify setup**

Run: `pytest --collect-only`
Expected: completes with "no tests ran" and no import errors (there are no test files yet).

- [ ] **Step 9: Commit**

```bash
git add requirements.txt .gitignore pytest.ini core storage scraper web sample_data notebook tests scripts
git commit -m "chore: project scaffolding and dependencies"
```

---

## Task 2: Core Data Models

**Files:**
- Create: `core/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
from core.models import Item, BasketEntry, BasketResult


def test_item_protein_per_unit():
    item = Item(
        id="chicken_breast", name="Chicken Breast", category="protein",
        unit_grams=500, unit_label="500g pack", protein_per_100g=31,
        coles_search_term="chicken breast", aldi_search_term="chicken breast",
    )
    assert item.protein_per_unit == 155.0


def test_basket_result_totals():
    item = Item(
        id="eggs", name="Eggs", category="protein", unit_grams=600,
        unit_label="dozen", protein_per_100g=13,
        coles_search_term="eggs 12 pack", aldi_search_term="eggs 12 pack",
    )
    entry = BasketEntry(item=item, store="coles", price=4.50)
    result = BasketResult(entries=[entry], budget=10.0)
    assert result.total_spent == 4.50
    assert result.total_protein == 78.0
    assert result.item_ids == {"eggs"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.models'`

- [ ] **Step 3: Write `core/models.py`**

```python
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


@dataclass
class BasketEntry:
    item: Item
    store: str
    price: float

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add core/models.py tests/test_models.py
git commit -m "feat: core data models for items, prices, recipes, and baskets"
```

---

## Task 3: Items & Recipes Data Files + Repositories

**Files:**
- Create: `data/items.yaml`
- Create: `data/recipes.json`
- Create: `core/items_repo.py`
- Create: `core/recipes_repo.py`
- Test: `tests/test_items_repo.py`
- Test: `tests/test_recipes_repo.py`

- [ ] **Step 1: Write `data/items.yaml`** (the `data/` directory was created in Task 1, Step 1)

```yaml
items:
  - id: chicken_breast
    name: Chicken Breast
    category: protein
    unit_grams: 500
    unit_label: 500g pack
    protein_per_100g: 31
    coles_search_term: chicken breast
    aldi_search_term: chicken breast
  - id: eggs
    name: Eggs
    category: protein
    unit_grams: 600
    unit_label: dozen
    protein_per_100g: 13
    coles_search_term: eggs 12 pack
    aldi_search_term: eggs 12 pack
  - id: canned_tuna
    name: Canned Tuna
    category: protein
    unit_grams: 185
    unit_label: 185g can
    protein_per_100g: 26
    coles_search_term: canned tuna
    aldi_search_term: canned tuna
  - id: lentils
    name: Dried Lentils
    category: protein
    unit_grams: 500
    unit_label: 500g bag
    protein_per_100g: 24
    coles_search_term: dried lentils
    aldi_search_term: dried lentils
  - id: chickpeas
    name: Canned Chickpeas
    category: protein
    unit_grams: 400
    unit_label: 400g can
    protein_per_100g: 7
    coles_search_term: canned chickpeas
    aldi_search_term: canned chickpeas
  - id: greek_yogurt
    name: Greek Yogurt
    category: protein
    unit_grams: 700
    unit_label: 700g tub
    protein_per_100g: 10
    coles_search_term: greek yogurt
    aldi_search_term: greek yogurt
  - id: milk
    name: Milk
    category: protein
    unit_grams: 2000
    unit_label: 2L
    protein_per_100g: 3.4
    coles_search_term: full cream milk 2l
    aldi_search_term: full cream milk 2l
  - id: tofu
    name: Firm Tofu
    category: protein
    unit_grams: 300
    unit_label: 300g pack
    protein_per_100g: 8
    coles_search_term: firm tofu
    aldi_search_term: firm tofu
  - id: beef_mince
    name: Beef Mince
    category: protein
    unit_grams: 500
    unit_label: 500g pack
    protein_per_100g: 26
    coles_search_term: beef mince
    aldi_search_term: beef mince
  - id: cottage_cheese
    name: Cottage Cheese
    category: protein
    unit_grams: 250
    unit_label: 250g tub
    protein_per_100g: 11
    coles_search_term: cottage cheese
    aldi_search_term: cottage cheese
  - id: salmon_canned
    name: Canned Salmon
    category: protein
    unit_grams: 210
    unit_label: 210g can
    protein_per_100g: 22
    coles_search_term: canned salmon
    aldi_search_term: canned salmon
  - id: cheese
    name: Cheddar Cheese
    category: protein
    unit_grams: 250
    unit_label: 250g block
    protein_per_100g: 25
    coles_search_term: cheddar cheese
    aldi_search_term: cheddar cheese
  - id: rice
    name: Rice
    category: carbs
    unit_grams: 1000
    unit_label: 1kg bag
    protein_per_100g: 7
    coles_search_term: white rice 1kg
    aldi_search_term: white rice 1kg
  - id: pasta
    name: Pasta
    category: carbs
    unit_grams: 500
    unit_label: 500g pack
    protein_per_100g: 13
    coles_search_term: pasta
    aldi_search_term: pasta
  - id: bread
    name: Bread
    category: carbs
    unit_grams: 700
    unit_label: 700g loaf
    protein_per_100g: 9
    coles_search_term: white bread loaf
    aldi_search_term: white bread loaf
  - id: oats
    name: Rolled Oats
    category: carbs
    unit_grams: 750
    unit_label: 750g pack
    protein_per_100g: 13
    coles_search_term: rolled oats
    aldi_search_term: rolled oats
  - id: potatoes
    name: Potatoes
    category: carbs
    unit_grams: 2000
    unit_label: 2kg bag
    protein_per_100g: 2
    coles_search_term: potatoes 2kg
    aldi_search_term: potatoes 2kg
  - id: onion
    name: Onion
    category: veg
    unit_grams: 1000
    unit_label: 1kg bag
    protein_per_100g: 1.1
    coles_search_term: brown onions 1kg
    aldi_search_term: brown onions 1kg
  - id: carrot
    name: Carrot
    category: veg
    unit_grams: 1000
    unit_label: 1kg bag
    protein_per_100g: 0.9
    coles_search_term: carrots 1kg
    aldi_search_term: carrots 1kg
  - id: frozen_mixed_veg
    name: Frozen Mixed Vegetables
    category: veg
    unit_grams: 1000
    unit_label: 1kg bag
    protein_per_100g: 2.5
    coles_search_term: frozen mixed vegetables
    aldi_search_term: frozen mixed vegetables
  - id: banana
    name: Banana
    category: veg
    unit_grams: 1000
    unit_label: 1kg
    protein_per_100g: 1.1
    coles_search_term: bananas
    aldi_search_term: bananas
  - id: apple
    name: Apple
    category: veg
    unit_grams: 1000
    unit_label: 1kg bag
    protein_per_100g: 0.3
    coles_search_term: apples 1kg
    aldi_search_term: apples 1kg
  - id: frozen_berries
    name: Frozen Mixed Berries
    category: veg
    unit_grams: 500
    unit_label: 500g pack
    protein_per_100g: 0.7
    coles_search_term: frozen mixed berries
    aldi_search_term: frozen mixed berries
  - id: olive_oil
    name: Olive Oil
    category: pantry
    unit_grams: 500
    unit_label: 500ml bottle
    protein_per_100g: 0
    coles_search_term: olive oil 500ml
    aldi_search_term: olive oil 500ml
  - id: canned_tomatoes
    name: Canned Tomatoes
    category: pantry
    unit_grams: 400
    unit_label: 400g can
    protein_per_100g: 1.2
    coles_search_term: canned tomatoes
    aldi_search_term: canned tomatoes
  - id: peanut_butter
    name: Peanut Butter
    category: pantry
    unit_grams: 500
    unit_label: 500g jar
    protein_per_100g: 25
    coles_search_term: peanut butter
    aldi_search_term: peanut butter
  - id: baked_beans
    name: Baked Beans
    category: pantry
    unit_grams: 420
    unit_label: 420g can
    protein_per_100g: 5.6
    coles_search_term: baked beans
    aldi_search_term: baked beans
  - id: almonds
    name: Almonds
    category: pantry
    unit_grams: 200
    unit_label: 200g pack
    protein_per_100g: 21
    coles_search_term: almonds
    aldi_search_term: almonds
```

- [ ] **Step 2: Write `data/recipes.json`** (write it in two halves if easier to paste; the file is one JSON object)

First half of the `recipes` array:
```json
{
  "recipes": [
    {"id": "chicken_rice_stir_fry", "name": "Chicken & Rice Stir-Fry", "servings": 4, "protein_per_serving": 35, "ingredients": ["chicken_breast", "rice", "carrot", "onion", "frozen_mixed_veg"], "method": "Stir-fry diced chicken breast with onion and carrot, add frozen mixed veg, serve over cooked rice."},
    {"id": "lentil_curry", "name": "Lentil Curry", "servings": 4, "protein_per_serving": 18, "ingredients": ["lentils", "onion", "canned_tomatoes", "rice"], "method": "Simmer lentils with onion and canned tomatoes until soft, season as a curry, serve with rice."},
    {"id": "egg_fried_rice", "name": "Egg Fried Rice", "servings": 3, "protein_per_serving": 16, "ingredients": ["eggs", "rice", "carrot", "onion", "frozen_mixed_veg"], "method": "Scramble eggs, mix through fried rice with diced carrot, onion and mixed veg."},
    {"id": "tuna_chickpea_salad", "name": "Tuna & Chickpea Salad", "servings": 2, "protein_per_serving": 28, "ingredients": ["canned_tuna", "chickpeas", "onion", "olive_oil"], "method": "Toss canned tuna and chickpeas with diced onion and a drizzle of olive oil."},
    {"id": "tofu_scramble", "name": "Tofu Scramble", "servings": 2, "protein_per_serving": 14, "ingredients": ["tofu", "onion", "carrot", "frozen_mixed_veg"], "method": "Crumble and pan-fry tofu with onion, carrot and mixed veg, season like scrambled eggs."},
    {"id": "beef_mince_pasta", "name": "Beef Mince Pasta", "servings": 4, "protein_per_serving": 30, "ingredients": ["beef_mince", "pasta", "canned_tomatoes", "onion"], "method": "Brown beef mince with onion, simmer in canned tomatoes, serve over pasta."},
    {"id": "greek_yogurt_oat_bowl", "name": "Greek Yogurt Oat Bowl", "servings": 1, "protein_per_serving": 20, "ingredients": ["greek_yogurt", "oats", "banana"], "method": "Combine oats with Greek yogurt, top with sliced banana."},
    {"id": "cottage_cheese_toast", "name": "Cottage Cheese Toast", "servings": 1, "protein_per_serving": 15, "ingredients": ["cottage_cheese", "bread", "apple"], "method": "Spread cottage cheese on toasted bread, serve with apple slices."},
    {"id": "chicken_baked_potato", "name": "Chicken Baked Potato", "servings": 2, "protein_per_serving": 32, "ingredients": ["chicken_breast", "potatoes", "frozen_mixed_veg"], "method": "Bake potatoes, top with shredded cooked chicken breast and steamed mixed veg."},
    {"id": "salmon_rice_bowl", "name": "Salmon Rice Bowl", "servings": 2, "protein_per_serving": 24, "ingredients": ["salmon_canned", "rice", "carrot", "onion"], "method": "Flake canned salmon over rice with sauteed carrot and onion."},
    {"id": "baked_beans_toast", "name": "Baked Beans on Toast", "servings": 2, "protein_per_serving": 18, "ingredients": ["baked_beans", "bread", "cheese"], "method": "Heat baked beans, serve on toast topped with grated cheese."},
    {"id": "chickpea_pasta_bake", "name": "Chickpea Pasta Bake", "servings": 4, "protein_per_serving": 22, "ingredients": ["chickpeas", "pasta", "canned_tomatoes", "cheese"], "method": "Mix chickpeas and pasta with canned tomatoes, top with cheese and bake."},
    {"id": "peanut_butter_oat_smoothie", "name": "Peanut Butter Oat Smoothie", "servings": 1, "protein_per_serving": 18, "ingredients": ["peanut_butter", "oats", "milk", "banana"], "method": "Blend peanut butter, oats, milk and banana into a smoothie."},
    {"id": "tuna_pasta_bake", "name": "Tuna Pasta Bake", "servings": 4, "protein_per_serving": 26, "ingredients": ["canned_tuna", "pasta", "canned_tomatoes", "cheese"], "method": "Mix tuna and pasta with canned tomatoes, top with cheese and bake."},
    {"id": "egg_and_toast", "name": "Eggs on Toast", "servings": 1, "protein_per_serving": 20, "ingredients": ["eggs", "bread", "cheese"], "method": "Fry or boil eggs, serve on toast with a slice of cheese."},
    {"id": "beef_mince_stuffed_potato", "name": "Beef Mince Stuffed Potato", "servings": 2, "protein_per_serving": 28, "ingredients": ["beef_mince", "potatoes", "onion", "cheese"], "method": "Bake potatoes, fill with cooked beef mince and onion, top with cheese."},
```

Second half (continuing the same `recipes` array, closing the JSON object):
```json
    {"id": "lentil_rice_bowl", "name": "Lentil Rice Bowl", "servings": 4, "protein_per_serving": 16, "ingredients": ["lentils", "rice", "carrot", "onion"], "method": "Cook lentils with onion and carrot, serve over rice."},
    {"id": "almond_yogurt_bowl", "name": "Almond Yogurt Bowl", "servings": 1, "protein_per_serving": 15, "ingredients": ["greek_yogurt", "almonds", "banana", "apple"], "method": "Top Greek yogurt with chopped almonds, banana and apple."},
    {"id": "tofu_stir_fry_noodle", "name": "Tofu Stir-Fry with Pasta", "servings": 3, "protein_per_serving": 16, "ingredients": ["tofu", "pasta", "carrot", "onion", "frozen_mixed_veg"], "method": "Stir-fry tofu with carrot, onion and mixed veg, toss through cooked pasta."},
    {"id": "chicken_salad_sandwich", "name": "Chicken Salad Sandwich", "servings": 2, "protein_per_serving": 26, "ingredients": ["chicken_breast", "bread", "onion"], "method": "Shred cooked chicken breast, mix with diced onion, serve in a sandwich."},
    {"id": "cheese_omelette", "name": "Cheese Omelette", "servings": 1, "protein_per_serving": 24, "ingredients": ["eggs", "cheese", "onion"], "method": "Whisk eggs, cook with diced onion, fold in cheese for an omelette."},
    {"id": "canned_salmon_jacket_potato", "name": "Salmon Jacket Potato", "servings": 2, "protein_per_serving": 26, "ingredients": ["salmon_canned", "potatoes", "cottage_cheese"], "method": "Bake potatoes, top with flaked canned salmon and a spoon of cottage cheese."},
    {"id": "beef_mince_fried_rice", "name": "Beef Mince Fried Rice", "servings": 4, "protein_per_serving": 28, "ingredients": ["beef_mince", "rice", "carrot", "onion", "frozen_mixed_veg"], "method": "Brown beef mince, stir-fry with rice, carrot, onion and mixed veg."},
    {"id": "chickpea_salad", "name": "Chickpea Salad", "servings": 2, "protein_per_serving": 12, "ingredients": ["chickpeas", "onion", "carrot", "olive_oil"], "method": "Toss chickpeas with diced onion and carrot, dress with olive oil."},
    {"id": "baked_beans_jacket_potato", "name": "Baked Beans Jacket Potato", "servings": 2, "protein_per_serving": 20, "ingredients": ["baked_beans", "potatoes", "cheese"], "method": "Bake potatoes, top with heated baked beans and grated cheese."},
    {"id": "tuna_baked_potato", "name": "Tuna Baked Potato", "servings": 2, "protein_per_serving": 27, "ingredients": ["canned_tuna", "potatoes", "cottage_cheese"], "method": "Bake potatoes, top with canned tuna mixed with cottage cheese."},
    {"id": "peanut_butter_banana_toast", "name": "Peanut Butter Banana Toast", "servings": 1, "protein_per_serving": 12, "ingredients": ["peanut_butter", "bread", "banana"], "method": "Spread peanut butter on toast, top with sliced banana."},
    {"id": "lentil_tomato_soup", "name": "Lentil Tomato Soup", "servings": 4, "protein_per_serving": 14, "ingredients": ["lentils", "canned_tomatoes", "onion", "carrot"], "method": "Simmer lentils, canned tomatoes, onion and carrot into a soup."},
    {"id": "tofu_curry", "name": "Tofu Curry", "servings": 3, "protein_per_serving": 14, "ingredients": ["tofu", "canned_tomatoes", "onion", "rice"], "method": "Simmer tofu and onion in canned tomatoes as a curry, serve with rice."},
    {"id": "egg_veg_fried_rice", "name": "Egg & Veg Fried Rice", "servings": 3, "protein_per_serving": 15, "ingredients": ["eggs", "rice", "frozen_mixed_veg", "onion"], "method": "Scramble eggs with fried rice, onion and frozen mixed veg."},
    {"id": "almond_berry_yogurt", "name": "Almond Berry Yogurt", "servings": 1, "protein_per_serving": 16, "ingredients": ["greek_yogurt", "almonds", "frozen_berries"], "method": "Top Greek yogurt with chopped almonds and frozen berries."},
    {"id": "beef_mince_chickpea_stew", "name": "Beef Mince & Chickpea Stew", "servings": 4, "protein_per_serving": 32, "ingredients": ["beef_mince", "chickpeas", "canned_tomatoes", "onion"], "method": "Brown beef mince with onion, add chickpeas and canned tomatoes, simmer as a stew."}
  ]
}
```

- [ ] **Step 3: Write the failing repo tests**

`tests/test_items_repo.py`:
```python
from core.items_repo import load_items


def test_load_items_returns_expected_count_and_fields():
    items = load_items()
    assert len(items) >= 25
    chicken = items["chicken_breast"]
    assert chicken.name == "Chicken Breast"
    assert chicken.category == "protein"
    assert chicken.protein_per_unit == chicken.protein_per_100g * chicken.unit_grams / 100.0


def test_all_items_have_required_fields():
    items = load_items()
    for item in items.values():
        assert item.coles_search_term
        assert item.aldi_search_term
        assert item.unit_grams > 0
```

`tests/test_recipes_repo.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/test_items_repo.py tests/test_recipes_repo.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 5: Write `core/items_repo.py`**

```python
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
```

- [ ] **Step 6: Write `core/recipes_repo.py`**

```python
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
        )
        for entry in raw["recipes"]
    ]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_items_repo.py tests/test_recipes_repo.py -v`
Expected: PASS (4 passed)

- [ ] **Step 8: Commit**

```bash
git add data/items.yaml data/recipes.json core/items_repo.py core/recipes_repo.py tests/test_items_repo.py tests/test_recipes_repo.py
git commit -m "feat: staple item and recipe data catalogs with loaders"
```

---

## Task 4: SQLite Storage Layer

**Files:**
- Create: `storage/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

`tests/test_db.py`:
```python
from pathlib import Path

from storage.db import connect, insert_price, get_latest_prices, get_last_scrape_time


def test_insert_and_get_latest_prices_returns_most_recent_per_store():
    conn = connect(Path(":memory:"))
    insert_price(conn, "eggs", "coles", 4.50, "2026-01-01T10:00:00")
    insert_price(conn, "eggs", "coles", 4.20, "2026-01-02T10:00:00")
    insert_price(conn, "eggs", "aldi", 3.90, "2026-01-02T09:00:00")

    latest = get_latest_prices(conn)

    assert latest["eggs"]["coles"] == (4.20, "2026-01-02T10:00:00")
    assert latest["eggs"]["aldi"] == (3.90, "2026-01-02T09:00:00")


def test_get_last_scrape_time_returns_none_when_empty():
    conn = connect(Path(":memory:"))
    assert get_last_scrape_time(conn) is None


def test_get_last_scrape_time_returns_max_timestamp():
    conn = connect(Path(":memory:"))
    insert_price(conn, "eggs", "coles", 4.50, "2026-01-01T10:00:00")
    insert_price(conn, "milk", "aldi", 2.10, "2026-01-03T08:00:00")
    assert get_last_scrape_time(conn) == "2026-01-03T08:00:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'storage.db'`

- [ ] **Step 3: Write `storage/db.py`**

```python
"""SQLite-backed price cache."""
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "prices.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    store TEXT NOT NULL,
    price REAL NOT NULL,
    scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_item_store ON prices(item_id, store);
"""


def connect(path: Path = None) -> sqlite3.Connection:
    if path is None:
        path = DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    return conn


def insert_price(conn: sqlite3.Connection, item_id: str, store: str, price: float, scraped_at: str) -> None:
    conn.execute(
        "INSERT INTO prices (item_id, store, price, scraped_at) VALUES (?, ?, ?, ?)",
        (item_id, store, price, scraped_at),
    )
    conn.commit()


def get_latest_prices(conn: sqlite3.Connection) -> dict:
    """Returns {item_id: {store: (price, scraped_at)}} using the most recent row per item/store."""
    rows = conn.execute(
        """
        SELECT item_id, store, price, scraped_at
        FROM prices p
        WHERE scraped_at = (
            SELECT MAX(scraped_at) FROM prices
            WHERE item_id = p.item_id AND store = p.store
        )
        """
    ).fetchall()
    result = {}
    for item_id, store, price, scraped_at in rows:
        result.setdefault(item_id, {})[store] = (price, scraped_at)
    return result


def get_last_scrape_time(conn: sqlite3.Connection):
    row = conn.execute("SELECT MAX(scraped_at) FROM prices").fetchone()
    return row[0] if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add storage/db.py tests/test_db.py
git commit -m "feat: SQLite price cache with latest-price and last-scrape lookups"
```

---

## Task 5: Price Text Parsing Utility

**Files:**
- Create: `scraper/base.py`
- Test: `tests/test_price_parsing.py`

- [ ] **Step 1: Write the failing test**

`tests/test_price_parsing.py`:
```python
from scraper.base import parse_price_text


def test_parse_simple_dollar_price():
    assert parse_price_text("$8.50") == 8.50


def test_parse_price_with_trailing_text():
    assert parse_price_text("$12.00 each") == 12.00


def test_parse_plain_number():
    assert parse_price_text("8.5") == 8.5


def test_parse_price_with_thousands_comma():
    assert parse_price_text("$1,234.50") == 1234.50


def test_parse_returns_none_for_no_digits():
    assert parse_price_text("Out of stock") is None


def test_parse_returns_none_for_empty_string():
    assert parse_price_text("") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_price_parsing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scraper.base'`

- [ ] **Step 3: Write `scraper/base.py`**

```python
"""Shared helpers for turning raw scraped text into clean price floats."""
import re

PRICE_PATTERN = re.compile(r"(\d+(?:\.\d{1,2})?)")


def parse_price_text(text: str):
    """Extracts a price as a float from messy scraped text, e.g. '$8.50', '$12.00 each',
    '8.5'. Returns None if no number is found."""
    if not text:
        return None
    cleaned = text.replace(",", "")
    match = PRICE_PATTERN.search(cleaned)
    if not match:
        return None
    return float(match.group(1))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_price_parsing.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add scraper/base.py tests/test_price_parsing.py
git commit -m "feat: price text parsing utility"
```

---

## Task 6: Budget Optimizer

**Files:**
- Create: `core/optimizer.py`
- Test: `tests/test_optimizer.py`

- [ ] **Step 1: Write the failing test**

`tests/test_optimizer.py`:
```python
from core.models import Item
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
    assert result.item_ids == {"chicken"}
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
    assert result.item_ids == {"potato"}
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_optimizer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.optimizer'`

- [ ] **Step 3: Write `core/optimizer.py`**

```python
"""Greedy budget optimizer: picks the basket of staple items that maximizes
protein-grams-per-dollar within a budget, preferring whichever store is cheaper
per item."""
from core.models import BasketEntry, BasketResult


def cheapest_store_for_item(item_id: str, latest_prices: dict):
    """Given {item_id: {store: (price, scraped_at)}}, returns (store, price) for the
    cheapest available store for item_id, or None if no price is available."""
    stores = latest_prices.get(item_id)
    if not stores:
        return None
    best_store, (best_price, _) = min(stores.items(), key=lambda kv: kv[1][0])
    return best_store, best_price


def build_basket(items: dict, latest_prices: dict, budget: float) -> BasketResult:
    """items: {item_id: Item}. latest_prices: {item_id: {store: (price, scraped_at)}}.
    Greedily fills the basket in descending order of protein-per-dollar, skipping any
    item that would exceed the remaining budget (but continuing to consider the rest)."""
    candidates = []
    for item_id, item in items.items():
        cheapest = cheapest_store_for_item(item_id, latest_prices)
        if cheapest is None:
            continue
        store, price = cheapest
        if price <= 0:
            continue
        protein_per_dollar = item.protein_per_unit / price
        candidates.append((protein_per_dollar, item, store, price))

    candidates.sort(key=lambda c: c[0], reverse=True)

    entries = []
    spent = 0.0
    for _, item, store, price in candidates:
        if spent + price <= budget:
            entries.append(BasketEntry(item=item, store=store, price=price))
            spent += price

    return BasketResult(entries=entries, budget=budget)


def cheapest_single_item_price(items: dict, latest_prices: dict):
    """Returns the lowest available price across all tracked items, or None if no
    prices are cached at all. Used to build a helpful message when the budget is too
    low for any item."""
    prices = []
    for item_id in items:
        cheapest = cheapest_store_for_item(item_id, latest_prices)
        if cheapest:
            prices.append(cheapest[1])
    return min(prices) if prices else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_optimizer.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add core/optimizer.py tests/test_optimizer.py
git commit -m "feat: greedy protein-per-dollar budget optimizer"
```

---

## Task 7: Meal Matcher

**Files:**
- Create: `core/meals.py`
- Test: `tests/test_meals.py`

This module is deliberately generic — it just ranks recipes against *any* set of
available item IDs. Task 11 (the web app) calls it twice: once for "items you already
have," once for "have + what you'd buy" — that's where the two-section UI comes from.

- [ ] **Step 1: Write the failing test**

`tests/test_meals.py`:
```python
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
    result = suggest_meals(recipes, available_item_ids={"chicken", "rice", "onion"})
    assert [r.id for r in result] == ["a"]


def test_suggest_meals_ranks_by_protein_descending():
    recipes = [
        make_recipe("low", ["eggs"], 10),
        make_recipe("high", ["eggs"], 30),
    ]
    result = suggest_meals(recipes, available_item_ids={"eggs"})
    assert [r.id for r in result] == ["high", "low"]


def test_suggest_meals_respects_top_n():
    recipes = [make_recipe(str(i), ["eggs"], i) for i in range(10)]
    result = suggest_meals(recipes, available_item_ids={"eggs"}, top_n=3)
    assert len(result) == 3


def test_suggest_meals_returns_empty_when_nothing_fits():
    recipes = [make_recipe("a", ["chicken"], 30)]
    result = suggest_meals(recipes, available_item_ids={"onion"})
    assert result == []


def test_suggest_meals_returns_empty_for_empty_item_set():
    recipes = [make_recipe("a", ["chicken"], 30)]
    result = suggest_meals(recipes, available_item_ids=set())
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_meals.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.meals'`

- [ ] **Step 3: Write `core/meals.py`**

```python
"""Matches a set of available item IDs against the curated recipe catalog."""


def suggest_meals(recipes: list, available_item_ids: set, top_n: int = 5) -> list:
    """Returns up to top_n recipes whose ingredients are fully covered by
    available_item_ids, ranked by protein_per_serving descending."""
    feasible = [r for r in recipes if r.ingredients and set(r.ingredients).issubset(available_item_ids)]
    feasible.sort(key=lambda r: r.protein_per_serving, reverse=True)
    return feasible[:top_n]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_meals.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/meals.py tests/test_meals.py
git commit -m "feat: recipe matcher ranked by protein per serving"
```

---

## Task 8: Coles Scraper

**Files:**
- Create: `scripts/capture_fixture.py`
- Create: `scraper/coles.py`
- Test: `tests/test_coles_scraper.py`
- Fixture: `tests/fixtures/coles_chicken_breast.html` (captured live, not hand-written)

Coles' site is a JS-rendered app, so prices are fetched with a real headless browser
(Playwright). The exact markup can only be known by looking at a live page, so this task
starts by capturing one.

- [ ] **Step 1: Write `scripts/capture_fixture.py`**

```python
"""One-off helper: fetches a live page with Playwright and saves its HTML to a fixture
file, so scraper parsers can be developed and tested against a real, frozen sample.

Usage:
    python scripts/capture_fixture.py coles "chicken breast" tests/fixtures/coles_chicken_breast.html
    python scripts/capture_fixture.py aldi "chicken breast" tests/fixtures/aldi_chicken_breast.html
"""
import asyncio
import sys

from playwright.async_api import async_playwright

URLS = {
    "coles": "https://www.coles.com.au/search?q={query}",
    "aldi": "https://www.aldi.com.au/en/weekly-specials/?searchTerm={query}",
}


async def capture(store: str, query: str, out_path: str) -> None:
    url = URLS[store].format(query=query.replace(" ", "+"))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)  # let client-side rendering settle
        html = await page.content()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        await browser.close()
    print(f"Saved {store} page for '{query}' to {out_path}")


if __name__ == "__main__":
    store_arg, query_arg, out_path_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    asyncio.run(capture(store_arg, query_arg, out_path_arg))
```

- [ ] **Step 2: Capture a live Coles fixture**

Run:
```bash
python scripts/capture_fixture.py coles "chicken breast" tests/fixtures/coles_chicken_breast.html
```
If this fails (timeout, blocked, CAPTCHA), that's useful information in itself — note it in the
README's limitations section when you get to Task 16, and skip ahead to Task 9 (Aldi) first;
come back and retry Coles later. Don't let one blocked site stall the whole plan.

- [ ] **Step 3: Inspect the fixture and find the price selector**

Open `tests/fixtures/coles_chicken_breast.html` in a text editor. Search (Ctrl+F) for a
dollar sign `$` near the first product's name. Note down:
- The exact price text you see (e.g. `$8.00`)
- The HTML tag and class/attribute wrapping that price (e.g. `<span class="price__value" data-testid="product-pricing">$8.00</span>`)

You'll use both in the next two steps. If the page looks like it has no product data at
all (e.g. a CAPTCHA/"are you human" page), note that in the README limitations section
and move on — the `fetch_price` function below is written to return `None` safely in
that situation.

- [ ] **Step 4: Write the failing parser test using what you found**

`tests/test_coles_scraper.py` — replace `EXPECTED_PRICE` and, if needed, the selector
passed to `BeautifulSoup.select_one` in Step 5 with what you actually observed:
```python
from pathlib import Path

from scraper.coles import parse_price_from_html

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "coles_chicken_breast.html"
EXPECTED_PRICE = 8.00  # <- replace with the price you observed in Step 3


def test_parse_price_from_real_fixture():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    assert parse_price_from_html(html) == EXPECTED_PRICE


def test_parse_price_from_html_returns_none_for_empty_page():
    assert parse_price_from_html("<html><body>no products</body></html>") is None
```

- [ ] **Step 5: Run test to verify it fails**

Run: `pytest tests/test_coles_scraper.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scraper.coles'`

- [ ] **Step 6: Write `scraper/coles.py`**

Use the selector you identified in Step 3 in place of the placeholder one below if it
differs (`'[data-testid="product-pricing"] .price__value'` is a reasonable starting
guess based on Coles' typical markup, but confirm it against your fixture):
```python
"""Coles.com.au price scraper.

Coles' site is a JS-rendered app, so prices are fetched with a real headless browser
(Playwright). If parse_price_from_html starts returning None for everything, Coles has
likely changed its markup — re-run scripts/capture_fixture.py for a fresh sample and
update the selector below.
"""
from bs4 import BeautifulSoup

from scraper.base import parse_price_text

SEARCH_URL_TEMPLATE = "https://www.coles.com.au/search?q={query}"
PRICE_SELECTOR = '[data-testid="product-pricing"] .price__value'


def parse_price_from_html(html: str):
    """Extracts the first product's price from a Coles search results page.
    Returns a float, or None if no price could be found."""
    soup = BeautifulSoup(html, "html.parser")
    price_el = soup.select_one(PRICE_SELECTOR)
    if price_el is None:
        return None
    return parse_price_text(price_el.get_text())


async def fetch_price(page, search_term: str):
    """Navigates `page` (a Playwright page) to the search results for `search_term` and
    returns the parsed price, or None on any failure. Never raises — callers treat None
    as 'could not get a price this time' and fall back to cached data."""
    try:
        await page.goto(SEARCH_URL_TEMPLATE.format(query=search_term.replace(" ", "+")), timeout=20000)
        await page.wait_for_selector(PRICE_SELECTOR, timeout=10000)
        html = await page.content()
        return parse_price_from_html(html)
    except Exception:
        return None
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_coles_scraper.py -v`
Expected: PASS (2 passed). If it still fails, re-open the fixture, re-check the selector
against the actual markup, and adjust `PRICE_SELECTOR` until it matches.

- [ ] **Step 8: Commit**

```bash
git add scripts/capture_fixture.py scraper/coles.py tests/test_coles_scraper.py tests/fixtures/coles_chicken_breast.html
git commit -m "feat: Coles price scraper with fixture-based parser test"
```

---

## Task 9: Aldi Scraper

**Files:**
- Create: `scraper/aldi.py`
- Test: `tests/test_aldi_scraper.py`
- Fixture: `tests/fixtures/aldi_chicken_breast.html` (captured live, not hand-written)

Same approach as Task 8, aimed at Aldi's Weekly Specials page instead. Remember Aldi
only lists its current Specials online, not a full catalog — this scraper will often
return `None` for items not currently on special, and that's expected, not a bug (the
web app already handles it via the "Coles only this week" messaging in Task 11).

- [ ] **Step 1: Capture a live Aldi fixture**

Run:
```bash
python scripts/capture_fixture.py aldi "chicken breast" tests/fixtures/aldi_chicken_breast.html
```

- [ ] **Step 2: Inspect the fixture and find the price selector**

Same process as Task 8, Step 3: open the file, search for `$`, note the price and the
element wrapping it.

- [ ] **Step 3: Write the failing parser test**

`tests/test_aldi_scraper.py` — replace `EXPECTED_PRICE` with what you observed:
```python
from pathlib import Path

from scraper.aldi import parse_price_from_html

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "aldi_chicken_breast.html"
EXPECTED_PRICE = 8.00  # <- replace with the price you observed


def test_parse_price_from_real_fixture():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    assert parse_price_from_html(html) == EXPECTED_PRICE


def test_parse_price_from_html_returns_none_for_empty_page():
    assert parse_price_from_html("<html><body>no products</body></html>") is None
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_aldi_scraper.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scraper.aldi'`

- [ ] **Step 5: Write `scraper/aldi.py`**

Adjust `PRICE_SELECTOR` to match what you found in Step 2:
```python
"""Aldi.com.au Weekly Specials price scraper.

Aldi only publishes current Specials online (not a full grocery catalog), so this
returns None for most items most of the time — that's expected, not a bug. If it starts
returning None for everything including items you know are on special, Aldi has likely
changed its markup — re-run scripts/capture_fixture.py and update the selector below.
"""
from bs4 import BeautifulSoup

from scraper.base import parse_price_text

SEARCH_URL_TEMPLATE = "https://www.aldi.com.au/en/weekly-specials/?searchTerm={query}"
PRICE_SELECTOR = ".product-tile__price"


def parse_price_from_html(html: str):
    """Extracts the first matching product's price from an Aldi Specials search page.
    Returns a float, or None if no price could be found (including when the item simply
    isn't on special this week)."""
    soup = BeautifulSoup(html, "html.parser")
    price_el = soup.select_one(PRICE_SELECTOR)
    if price_el is None:
        return None
    return parse_price_text(price_el.get_text())


async def fetch_price(page, search_term: str):
    """Navigates `page` (a Playwright page) to the Specials search for `search_term` and
    returns the parsed price, or None on any failure or when nothing is on special. Never
    raises — callers treat None as 'no current Aldi price' and show that in the UI."""
    try:
        await page.goto(SEARCH_URL_TEMPLATE.format(query=search_term.replace(" ", "+")), timeout=20000)
        await page.wait_for_timeout(2000)
        html = await page.content()
        return parse_price_from_html(html)
    except Exception:
        return None
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_aldi_scraper.py -v`
Expected: PASS (2 passed). Adjust `PRICE_SELECTOR` against the real fixture if it fails.

- [ ] **Step 7: Commit**

```bash
git add scraper/aldi.py tests/test_aldi_scraper.py tests/fixtures/aldi_chicken_breast.html
git commit -m "feat: Aldi Specials price scraper with fixture-based parser test"
```

---

## Task 10: Scrape Orchestration

**Files:**
- Create: `scraper/run_scrape.py`
- Test: `tests/test_run_scrape.py`

- [ ] **Step 1: Write the failing test**

`tests/test_run_scrape.py`:
```python
from pathlib import Path

from core.models import Item
from scraper import run_scrape
from storage.db import connect, get_latest_prices


def make_item(id):
    return Item(id=id, name=id, category="protein", unit_grams=500, unit_label="unit",
                protein_per_100g=20, coles_search_term=id, aldi_search_term=id)


async def test_scrape_all_writes_successful_prices_and_skips_failures(monkeypatch):
    items = {"eggs": make_item("eggs"), "milk": make_item("milk")}
    conn = connect(Path(":memory:"))

    async def fake_coles_fetch(page, term):
        return 4.50 if term == "eggs" else None

    async def fake_aldi_fetch(page, term):
        return 3.90  # aldi "succeeds" for every item in this test

    monkeypatch.setattr(run_scrape.coles, "fetch_price", fake_coles_fetch)
    monkeypatch.setattr(run_scrape.aldi, "fetch_price", fake_aldi_fetch)

    written = await run_scrape.scrape_all(page=None, items=items, conn=conn)

    assert written == 3  # eggs/coles + eggs/aldi + milk/aldi (milk/coles returned None)
    latest = get_latest_prices(conn)
    assert latest["eggs"]["coles"][0] == 4.50
    assert "coles" not in latest.get("milk", {})
    assert latest["milk"]["aldi"][0] == 3.90
```

Note: `asyncio_mode = auto` in `pytest.ini` (from Task 1) lets plain `async def test_...`
functions run directly, no `@pytest.mark.asyncio` decorator needed.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_run_scrape.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scraper.run_scrape'`

- [ ] **Step 3: Write `scraper/run_scrape.py`**

```python
"""Orchestrates scraping all tracked items from Coles and Aldi, writing results to
SQLite. Tolerates partial failure: one item or store failing never aborts the run."""
import asyncio
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from core.items_repo import load_items
from scraper import coles, aldi
from storage.db import connect, insert_price


async def scrape_all(page, items: dict, conn) -> int:
    """Given an already-open Playwright page (or None, if fetch functions are mocked),
    a loaded items dict, and a DB connection, scrapes each item from both stores and
    writes successful results. Returns the number of price records written."""
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for item in items.values():
        coles_price = await coles.fetch_price(page, item.coles_search_term)
        if coles_price is not None:
            insert_price(conn, item.id, "coles", coles_price, now)
            written += 1

        aldi_price = await aldi.fetch_price(page, item.aldi_search_term)
        if aldi_price is not None:
            insert_price(conn, item.id, "aldi", aldi_price, now)
            written += 1
    return written


async def run() -> int:
    """Entry point: loads items, opens a real browser, scrapes everything, writes to
    the default SQLite DB."""
    items = load_items()
    conn = connect()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        written = await scrape_all(page, items, conn)
        await browser.close()
    return written


if __name__ == "__main__":
    count = asyncio.run(run())
    print(f"Wrote {count} price records.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_run_scrape.py -v`
Expected: PASS (1 passed) — note this test never launches a real browser; `page=None` is
fine because `coles.fetch_price`/`aldi.fetch_price` are mocked and never touch it.

- [ ] **Step 5: Commit**

```bash
git add scraper/run_scrape.py tests/test_run_scrape.py
git commit -m "feat: scrape orchestration tolerant of per-item/per-store failures"
```

---

## Task 11: FastAPI Web App

**Files:**
- Create: `web/app.py`
- Create: `web/templates/index.html`
- Create: `web/templates/results.html`
- Create: `web/static/style.css`
- Test: `tests/test_web_app.py`

The budget form includes a checklist of "items you already have" (the pantry feature).
The results page shows two meal sections: meals you can make right now from what you
already have, and additional meals unlocked by buying the optimizer's basket.

- [ ] **Step 1: Write the failing tests**

`tests/test_web_app.py`:
```python
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
```

```python
def test_plan_with_no_price_data_still_shows_pantry_meals(client):
    response = client.post("/plan", data={"budget": "20", "have_items": ["eggs", "cheese", "onion"]})
    assert response.status_code == 200
    assert "run the scraper" in response.text.lower()
    assert "Cheese Omelette" in response.text  # eggs + cheese + onion, no shopping needed


def test_plan_with_no_pantry_items_shows_no_pantry_meals_message(client):
    response = client.post("/plan", data={"budget": "20"})
    assert response.status_code == 200
    assert "right now" in response.text.lower()
```

```python
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
    # eggs + onion already owned, cheese gets bought -> Cheese Omelette becomes feasible
    assert "Cheese Omelette" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_web_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'web.app'`

- [ ] **Step 3: Write `web/templates/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ProteinBudget Planner</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <main>
        <h1>ProteinBudget Planner</h1>
        <p>Enter your grocery budget to see the cheapest basket from Coles &amp; Aldi (Sydney), plus high-protein meals you can make.</p>
        <form action="/plan" method="post">
            <label for="budget">Budget (AUD)</label>
            <input type="number" id="budget" name="budget" min="1" step="0.01" required>

            <fieldset>
                <legend>Items you already have (optional)</legend>
                {% for item in items.values() %}
                    <label class="checkbox-row">
                        <input type="checkbox" name="have_items" value="{{ item.id }}"> {{ item.name }}
                    </label>
                {% endfor %}
            </fieldset>

            <button type="submit">Find my groceries</button>
        </form>
    </main>
</body>
</html>
```

- [ ] **Step 4: Write `web/templates/results.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ProteinBudget Planner — Results</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <main>
        <h1>Your plan for ${{ "%.2f"|format(budget) }}</h1>

        <section>
            <h2>Meals you can make right now</h2>
            {% if pantry_meals %}
                <ul>
                    {% for meal in pantry_meals %}
                        <li><strong>{{ meal.name }}</strong> — {{ "%.0f"|format(meal.protein_per_serving) }}g protein/serving, serves {{ meal.servings }}. {{ meal.method }}</li>
                    {% endfor %}
                </ul>
            {% else %}
                <p>No full meal matches from just what you've ticked yet — see what shopping unlocks below.</p>
            {% endif %}
        </section>
```

```html
        {% if error %}
            <p class="error">{{ error }}</p>
        {% else %}
            <section>
                <h2>Basket (total: ${{ "%.2f"|format(basket.total_spent) }}, {{ "%.1f"|format(basket.total_protein) }}g protein)</h2>
                <ul>
                    {% for entry in basket.entries %}
                        <li>{{ entry.item.name }} — {{ entry.store|capitalize }} — ${{ "%.2f"|format(entry.price) }} ({{ "%.0f"|format(entry.protein_total) }}g protein)</li>
                    {% endfor %}
                </ul>
            </section>

            <section>
                <h2>Meals you can make after this shop</h2>
                {% if shopping_meals %}
                    <ul>
                        {% for meal in shopping_meals %}
                            <li><strong>{{ meal.name }}</strong> — {{ "%.0f"|format(meal.protein_per_serving) }}g protein/serving, serves {{ meal.servings }}. {{ meal.method }}</li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <p>No additional full meal matches yet with this basket — try a larger budget.</p>
                {% endif %}
            </section>
        {% endif %}

        {% if last_scrape %}
            <p class="freshness">Prices last updated: {{ last_scrape }}</p>
        {% endif %}

        <a href="/">&larr; Try another budget</a>
    </main>
</body>
</html>
```

- [ ] **Step 5: Write `web/static/style.css`**

```css
body {
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 640px;
    margin: 2rem auto;
    padding: 0 1rem;
    color: #1a1a1a;
    background: #fafafa;
}
h1, h2 { color: #1a1a1a; }
form { margin: 1.5rem 0; }
form > label { display: block; margin-bottom: 0.5rem; font-weight: 600; }
input[type="number"] { padding: 0.5rem; font-size: 1rem; width: 120px; margin-bottom: 1rem; }
fieldset { margin: 1rem 0; border: 1px solid #ddd; border-radius: 4px; padding: 0.75rem; }
.checkbox-row { display: block; margin: 0.25rem 0; font-weight: normal; }
button {
    padding: 0.5rem 1rem; font-size: 1rem; background: #2a7f62; color: white;
    border: none; border-radius: 4px; cursor: pointer;
}
button:hover { background: #216650; }
.error { color: #b3261e; font-weight: bold; }
.freshness { color: #666; font-size: 0.9rem; }
ul { line-height: 1.6; }
a { color: #2a7f62; }
```

- [ ] **Step 6: Write `web/app.py`**

```python
"""FastAPI web app: a budget + pantry-checklist form, and a results page showing the
cheapest basket, meals makeable right now, and meals the basket would unlock."""
from pathlib import Path
from typing import List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.items_repo import load_items
from core.meals import suggest_meals
from core.optimizer import build_basket, cheapest_single_item_price
from core.recipes_repo import load_recipes
from storage.db import connect, get_last_scrape_time, get_latest_prices

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="ProteinBudget Planner")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    items = load_items()
    return templates.TemplateResponse("index.html", {"request": request, "items": items})
```

```python
@app.post("/plan", response_class=HTMLResponse)
def plan(request: Request, budget: float = Form(...), have_items: List[str] = Form([])):
    items = load_items()
    recipes = load_recipes()
    conn = connect()
    latest_prices = get_latest_prices(conn)
    last_scrape = get_last_scrape_time(conn)

    have_ids = set(have_items) & set(items.keys())
    pantry_meals = suggest_meals(recipes, have_ids, top_n=5)

    context = {
        "request": request, "budget": budget, "items": items,
        "pantry_meals": pantry_meals, "basket": None, "shopping_meals": [],
        "last_scrape": last_scrape, "error": None,
    }

    if not latest_prices:
        context["error"] = (
            "No price data yet. Run the scraper first (see README), or try again "
            "later if a previous scrape attempt failed."
        )
        return templates.TemplateResponse("results.html", context)

    basket = build_basket(items, latest_prices, budget)

    if not basket.entries:
        cheapest = cheapest_single_item_price(items, latest_prices)
        context["error"] = (
            f"The cheapest tracked item currently costs ${cheapest:.2f} — try a higher budget."
            if cheapest else "No items currently have a price. Try running the scraper again."
        )
        return templates.TemplateResponse("results.html", context)

    combined_ids = basket.item_ids | have_ids
    shopping_meals = [
        m for m in suggest_meals(recipes, combined_ids, top_n=10)
        if m.id not in {p.id for p in pantry_meals}
    ][:5]

    context["basket"] = basket
    context["shopping_meals"] = shopping_meals
    return templates.TemplateResponse("results.html", context)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_web_app.py -v`
Expected: PASS (5 passed)

- [ ] **Step 8: Commit**

```bash
git add web/app.py web/templates web/static tests/test_web_app.py
git commit -m "feat: web app with budget form, pantry checklist, and two-tier meal suggestions"
```

---

## Task 12: App Entry Point

**Files:**
- Create: `run.py`
- Test: `tests/test_run_entrypoint.py`

- [ ] **Step 1: Write the failing test**

`tests/test_run_entrypoint.py`:
```python
import run


def test_run_module_defines_host_and_port():
    assert run.HOST == "127.0.0.1"
    assert run.PORT == 8000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_run_entrypoint.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'run'`

- [ ] **Step 3: Write `run.py`**

```python
"""Entry point: starts the local FastAPI server and opens it in your browser.

Usage: python run.py
"""
import threading
import time
import webbrowser

import uvicorn

from web.app import app

HOST = "127.0.0.1"
PORT = 8000


def open_browser():
    time.sleep(1.5)  # give uvicorn a moment to start listening
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_run_entrypoint.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_run_entrypoint.py
git commit -m "feat: local entry point that starts the server and opens the browser"
```

---

## Task 13: Manual Live-Check Script

**Files:**
- Create: `scripts/live_check.py`

Not unit tested — this is a manual tool you run yourself to sanity-check the real
scrapers against the live sites whenever you want, independent of the automated suite.

- [ ] **Step 1: Write `scripts/live_check.py`**

```python
"""Manual sanity check: scrapes a few real items from Coles and Aldi and prints what it
found. Not run by the automated test suite — run this yourself whenever you want to
confirm the live scrapers still work against the real sites.

Usage: python scripts/live_check.py
"""
import asyncio

from playwright.async_api import async_playwright

from scraper import aldi, coles

CHECK_ITEMS = ["chicken breast", "eggs", "milk"]


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for term in CHECK_ITEMS:
            coles_price = await coles.fetch_price(page, term)
            aldi_price = await aldi.fetch_price(page, term)
            print(f"{term:20s} coles={coles_price}  aldi={aldi_price}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run it manually and eyeball the output**

Run: `python scripts/live_check.py`
Expected: three lines printed, one per item, each showing a numeric price or `None` for
each store. `None` for Aldi is normal (item not currently on special); `None` for both
on an item that should have a price suggests the scraper needs attention.

- [ ] **Step 3: Commit**

```bash
git add scripts/live_check.py
git commit -m "chore: manual live scraper sanity-check script"
```

---

## Task 14: Sample Data for Offline Demo

**Files:**
- Create: `sample_data/sample_prices.csv`
- Create: `sample_data/load_sample_data.py`
- Test: `tests/test_sample_data.py`

These are illustrative, made-up prices (clearly labeled as such) so the app, tests, and
notebook all produce real-looking output without requiring Playwright or a live scrape
first. `tofu` has no Aldi row on purpose — it demonstrates the "Coles only this week"
case the web app already handles.

- [ ] **Step 1: Write the failing test**

`tests/test_sample_data.py`:
```python
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
    tofu_stores = {row["store"] for row in rows if row["item_id"] == "tofu"}
    assert tofu_stores == {"coles"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sample_data.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sample_data.load_sample_data'`

- [ ] **Step 3: Write `sample_data/sample_prices.csv`** (first half of rows)

```csv
item_id,store,price,scraped_at
chicken_breast,coles,10.00,2026-10-18T09:00:00+00:00
chicken_breast,aldi,8.50,2026-10-18T09:00:00+00:00
eggs,coles,5.50,2026-10-18T09:00:00+00:00
eggs,aldi,4.80,2026-10-18T09:00:00+00:00
canned_tuna,coles,3.20,2026-10-18T09:00:00+00:00
canned_tuna,aldi,2.70,2026-10-18T09:00:00+00:00
lentils,coles,3.00,2026-10-18T09:00:00+00:00
lentils,aldi,2.40,2026-10-18T09:00:00+00:00
chickpeas,coles,1.60,2026-10-18T09:00:00+00:00
chickpeas,aldi,1.30,2026-10-18T09:00:00+00:00
greek_yogurt,coles,6.50,2026-10-18T09:00:00+00:00
greek_yogurt,aldi,5.20,2026-10-18T09:00:00+00:00
milk,coles,3.50,2026-10-18T09:00:00+00:00
milk,aldi,2.90,2026-10-18T09:00:00+00:00
tofu,coles,4.00,2026-10-18T09:00:00+00:00
beef_mince,coles,8.00,2026-10-18T09:00:00+00:00
beef_mince,aldi,6.90,2026-10-18T09:00:00+00:00
cottage_cheese,coles,4.50,2026-10-18T09:00:00+00:00
cottage_cheese,aldi,3.80,2026-10-18T09:00:00+00:00
salmon_canned,coles,4.20,2026-10-18T09:00:00+00:00
salmon_canned,aldi,3.50,2026-10-18T09:00:00+00:00
cheese,coles,5.00,2026-10-18T09:00:00+00:00
cheese,aldi,4.10,2026-10-18T09:00:00+00:00
rice,coles,2.50,2026-10-18T09:00:00+00:00
rice,aldi,2.00,2026-10-18T09:00:00+00:00
pasta,coles,1.80,2026-10-18T09:00:00+00:00
pasta,aldi,1.40,2026-10-18T09:00:00+00:00
bread,coles,3.80,2026-10-18T09:00:00+00:00
bread,aldi,3.00,2026-10-18T09:00:00+00:00
```

Append the second half of rows to the **same file** (don't overwrite it):

```csv
oats,coles,3.50,2026-10-18T09:00:00+00:00
oats,aldi,2.80,2026-10-18T09:00:00+00:00
potatoes,coles,4.50,2026-10-18T09:00:00+00:00
potatoes,aldi,3.90,2026-10-18T09:00:00+00:00
onion,coles,2.80,2026-10-18T09:00:00+00:00
onion,aldi,2.20,2026-10-18T09:00:00+00:00
carrot,coles,2.20,2026-10-18T09:00:00+00:00
carrot,aldi,1.80,2026-10-18T09:00:00+00:00
frozen_mixed_veg,coles,4.00,2026-10-18T09:00:00+00:00
frozen_mixed_veg,aldi,3.20,2026-10-18T09:00:00+00:00
banana,coles,3.90,2026-10-18T09:00:00+00:00
banana,aldi,3.40,2026-10-18T09:00:00+00:00
apple,coles,4.50,2026-10-18T09:00:00+00:00
apple,aldi,3.80,2026-10-18T09:00:00+00:00
frozen_berries,coles,5.50,2026-10-18T09:00:00+00:00
frozen_berries,aldi,4.50,2026-10-18T09:00:00+00:00
olive_oil,coles,9.00,2026-10-18T09:00:00+00:00
olive_oil,aldi,7.50,2026-10-18T09:00:00+00:00
canned_tomatoes,coles,1.50,2026-10-18T09:00:00+00:00
canned_tomatoes,aldi,1.10,2026-10-18T09:00:00+00:00
peanut_butter,coles,4.80,2026-10-18T09:00:00+00:00
peanut_butter,aldi,3.90,2026-10-18T09:00:00+00:00
baked_beans,coles,2.10,2026-10-18T09:00:00+00:00
baked_beans,aldi,1.70,2026-10-18T09:00:00+00:00
almonds,coles,6.00,2026-10-18T09:00:00+00:00
almonds,aldi,4.90,2026-10-18T09:00:00+00:00
```

- [ ] **Step 4: Write `sample_data/load_sample_data.py`**

```python
"""Loads the illustrative sample_prices.csv into the real SQLite price cache, so you can
see the app working end-to-end without installing Playwright or scraping live sites
first. These are made-up, illustrative prices for demo purposes only — NOT real current
prices. Run the real scraper (scraper/run_scrape.py) to get actual current prices.

Usage: python sample_data/load_sample_data.py
"""
import csv
from pathlib import Path

from storage.db import connect, insert_price

SAMPLE_CSV = Path(__file__).resolve().parent / "sample_prices.csv"


def main() -> None:
    conn = connect()
    count = 0
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            insert_price(conn, row["item_id"], row["store"], float(row["price"]), row["scraped_at"])
            count += 1
    print(f"Loaded {count} sample price records into prices.db")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_sample_data.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add sample_data/sample_prices.csv sample_data/load_sample_data.py tests/test_sample_data.py
git commit -m "feat: illustrative sample price data for offline demo"
```

---

## Task 15: Data Analysis Notebook

**Files:**
- Create: `notebook/build_notebook.py`
- Create: `notebook/analysis.ipynb` (generated, not hand-written)
- Test: `tests/test_notebook_build.py`

The notebook itself isn't unit-tested (per the design spec), but the script that
generates it is, so the notebook's structure stays reproducible and reviewable as code
rather than as raw, hard-to-diff JSON.

- [ ] **Step 1: Write the failing test**

`tests/test_notebook_build.py`:
```python
from notebook.build_notebook import build


def test_notebook_has_expected_structure():
    nb = build()
    assert len(nb["cells"]) == 9
    assert nb["cells"][0]["cell_type"] == "markdown"
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_notebook_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'notebook.build_notebook'`

- [ ] **Step 3: Write `notebook/build_notebook.py`**

```python
"""Generates notebook/analysis.ipynb. Run this whenever you want to (re)create the
notebook from its source cells below, rather than hand-editing raw ipynb JSON.

Usage: python notebook/build_notebook.py
"""
from pathlib import Path

import nbformat as nbf

OUT_PATH = Path(__file__).resolve().parent / "analysis.ipynb"


def build() -> "nbf.NotebookNode":
    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(
            "# ProteinBudget Planner — Price & Protein-Value Analysis\n\n"
            "Exploratory analysis of grocery prices cached by this project. Reads from "
            "`prices.db` if it exists (real scraped data), otherwise falls back to "
            "`sample_data/sample_prices.csv` (illustrative demo data)."
        ),
        nbf.v4.new_code_cell(
            "import sqlite3\n"
            "from pathlib import Path\n"
            "\n"
            "import pandas as pd\n"
            "\n"
            "ROOT = Path.cwd()\n"
            "DB_PATH = ROOT / 'prices.db'\n"
            "SAMPLE_CSV = ROOT / 'sample_data' / 'sample_prices.csv'\n"
            "\n"
            "if DB_PATH.exists():\n"
            "    conn = sqlite3.connect(DB_PATH)\n"
            "    prices = pd.read_sql_query('SELECT * FROM prices', conn)\n"
            "else:\n"
            "    prices = pd.read_csv(SAMPLE_CSV)\n"
            "\n"
            "prices.head()"
        ),
        nbf.v4.new_markdown_cell("## Load the item catalog (for protein-per-100g and unit sizes)"),
        nbf.v4.new_code_cell(
            "import yaml\n"
            "\n"
            "with open(ROOT / 'data' / 'items.yaml') as f:\n"
            "    items_raw = yaml.safe_load(f)['items']\n"
            "items_df = pd.DataFrame(items_raw)\n"
            "items_df['protein_per_unit'] = items_df['protein_per_100g'] * items_df['unit_grams'] / 100\n"
            "items_df.head()"
        ),
    ]
    return nb


if __name__ == "__main__":
    nb = build()
    nbf.write(nb, OUT_PATH)
    print(f"Wrote {OUT_PATH}")
```

(This is a partial cell list — Step 4 below adds the remaining cells to the same `cells`
list before this script is run.)

- [ ] **Step 4: Replace `notebook/build_notebook.py` with the complete version** (adds the
  remaining cells — this supersedes the partial version from Step 3; write this full file)

```python
"""Generates notebook/analysis.ipynb. Run this whenever you want to (re)create the
notebook from its source cells below, rather than hand-editing raw ipynb JSON.

Usage: python notebook/build_notebook.py
"""
from pathlib import Path

import nbformat as nbf

OUT_PATH = Path(__file__).resolve().parent / "analysis.ipynb"


def build() -> "nbf.NotebookNode":
    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(
            "# ProteinBudget Planner — Price & Protein-Value Analysis\n\n"
            "Exploratory analysis of grocery prices cached by this project. Reads from "
            "`prices.db` if it exists (real scraped data), otherwise falls back to "
            "`sample_data/sample_prices.csv` (illustrative demo data)."
        ),
        nbf.v4.new_code_cell(
            "import sqlite3\n"
            "from pathlib import Path\n"
            "\n"
            "import pandas as pd\n"
            "\n"
            "ROOT = Path.cwd()\n"
            "DB_PATH = ROOT / 'prices.db'\n"
            "SAMPLE_CSV = ROOT / 'sample_data' / 'sample_prices.csv'\n"
            "\n"
            "if DB_PATH.exists():\n"
            "    conn = sqlite3.connect(DB_PATH)\n"
            "    prices = pd.read_sql_query('SELECT * FROM prices', conn)\n"
            "else:\n"
            "    prices = pd.read_csv(SAMPLE_CSV)\n"
            "\n"
            "prices.head()"
        ),
        nbf.v4.new_markdown_cell("## Load the item catalog (for protein-per-100g and unit sizes)"),
        nbf.v4.new_code_cell(
            "import yaml\n"
            "\n"
            "with open(ROOT / 'data' / 'items.yaml') as f:\n"
            "    items_raw = yaml.safe_load(f)['items']\n"
            "items_df = pd.DataFrame(items_raw)\n"
            "items_df['protein_per_unit'] = items_df['protein_per_100g'] * items_df['unit_grams'] / 100\n"
            "items_df.head()"
        ),
        nbf.v4.new_markdown_cell("## Latest price per item/store, merged with protein data, ranked by protein-per-dollar"),
        nbf.v4.new_code_cell(
            "latest = prices.sort_values('scraped_at').groupby(['item_id', 'store']).tail(1)\n"
            "merged = latest.merge(items_df, left_on='item_id', right_on='id')\n"
            "merged['protein_per_dollar'] = merged['protein_per_unit'] / merged['price']\n"
            "merged[['name', 'store', 'price', 'protein_per_unit', 'protein_per_dollar']]\\n"
            "    .sort_values('protein_per_dollar', ascending=False).head(10)"
        ),
        nbf.v4.new_markdown_cell("## Coles vs Aldi: which store is cheaper per item?"),
        nbf.v4.new_code_cell(
            "pivot = merged.pivot_table(index='name', columns='store', values='price')\n"
            "pivot['cheaper_store'] = pivot.idxmin(axis=1)\n"
            "pivot"
        ),
        nbf.v4.new_code_cell(
            "import matplotlib.pyplot as plt\n"
            "\n"
            "top = merged.sort_values('protein_per_dollar', ascending=False).head(12)\n"
            "plt.figure(figsize=(8, 5))\n"
            "plt.barh(top['name'], top['protein_per_dollar'])\n"
            "plt.xlabel('Protein per dollar (g/$)')\n"
            "plt.title('Best protein value, by item')\n"
            "plt.gca().invert_yaxis()\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),
    ]
    return nb


if __name__ == "__main__":
    nb = build()
    nbf.write(nb, OUT_PATH)
    print(f"Wrote {OUT_PATH}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_notebook_build.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Generate the actual notebook file**

Run: `python notebook/build_notebook.py`
Expected: prints `Wrote .../notebook/analysis.ipynb`

- [ ] **Step 7: Commit**

```bash
git add notebook/build_notebook.py notebook/analysis.ipynb tests/test_notebook_build.py
git commit -m "feat: reproducible pandas/Jupyter analysis notebook"
```

---

## Task 16: README

**Files:**
- Create: `README.md`

This is the portfolio-facing document — write it as the final step so it can
accurately describe what was actually built, not what was planned.

- [ ] **Step 1: Write `README.md`**, Part 1 — title through Features:

```markdown
# ProteinBudget Planner

Find the cheapest way to spend a grocery budget across Coles and Aldi in Sydney,
and see which high-protein meals it unlocks — including meals you can already make
from what's in your pantry.

Built as a data science / applied engineering portfolio project: a small end-to-end
pipeline (scrape, cache, optimize, serve) with a pandas/Jupyter analysis layer on
top of the same data.

![screenshot placeholder](docs/screenshot.png)
*(Add your own screenshot here once you've run the app -- see "Getting Started" below.)*

## Why this exists

Grocery budgeting advice online is generic. This project answers a more specific
question: given a fixed number of dollars and the items already in your kitchen,
what is the highest-protein set of meals available to you right now, and what does
spending the rest of the budget unlock?

## Features

- Budget optimizer: greedily fills a basket of about 28 tracked grocery staples to
  maximize protein-grams-per-dollar within your budget, picking whichever of Coles or
  Aldi is cheaper for each item.
- Pantry-aware meal matching: tick off what you already have, and the app shows
  full high-protein meals you can make right now, separately from meals a shop would
  unlock.
- Live price scraping: a Playwright-driven scraper fetches current prices from
  Coles and Aldi on demand, cached locally in SQLite so the app doesn't re-scrape on
  every request.
- Offline-friendly: ships with illustrative sample price data, so the app, tests,
  and notebook all work out of the box without installing a browser or scraping
  anything first.
- Data analysis notebook: a pandas/Jupyter notebook over the same price cache --
  protein-per-dollar rankings, a Coles-vs-Aldi price comparison, and price history
  over time as the cache accumulates scrapes.
```

- [ ] **Step 2: Write `README.md`**, Part 2 — How It Works:

```markdown
## How it works

```
Scraper (Playwright) -> SQLite (prices.db) -> Optimizer / Meal Matcher -> FastAPI + HTML UI
                               |
                               v
                     pandas + Jupyter notebook   (separate, manual analysis)
```

1. You tick off items you already have and enter a budget.
2. The optimizer reads the latest cached prices and greedily builds the basket with
   the best protein-per-dollar that fits your budget -- skipping any item that doesn't
   fit but still filling in cheaper ones after it (not a simple "stop at the first
   thing that's too expensive").
3. The meal matcher checks the curated recipe catalog against (a) what you already
   have, and (b) what you have plus what the basket would add -- so you see "meals you
   can make right now" and "meals this shop unlocks" as two distinct lists.
4. If a scrape has never run, or fails, the app falls back to whatever is in the
   local price cache (including the bundled sample data) and shows a "prices last
   updated" timestamp so you always know how fresh what you're looking at is.
```

- [ ] **Step 3: Write `README.md`**, Part 3 — Tech Stack and Getting Started:

```markdown
## Tech stack

Python 3.11+, FastAPI, Jinja2, Playwright (Chromium), BeautifulSoup4, SQLite,
PyYAML, pandas, matplotlib, pytest + pytest-asyncio

## Getting started

```bash
git clone <your-repo-url>
cd protein-budget-planner
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

(Use `source venv/bin/activate` instead of `venv\Scripts\activate` on macOS/Linux.
Installing the Playwright browser is only needed if you want live scraping.)

See it working immediately, without scraping anything:

```bash
python sample_data/load_sample_data.py
python run.py
```

This opens `http://localhost:8000` in your browser with illustrative sample prices
already loaded -- enter a budget and try ticking a few pantry items.

Get real current prices:

```bash
python scraper/run_scrape.py
```

This scrapes Coles and Aldi for every tracked item and writes results into
`prices.db`, overwriting the sample data's effect (the app always uses whichever
price is most recent per item/store). Re-run it any time to refresh.
```

- [ ] **Step 4: Write `README.md`**, Part 4 — Usage through Testing:

```markdown
## Usage

1. Run `python run.py` -- it starts a local server and opens your browser.
2. Enter your budget, and optionally tick items you already have.
3. Submit. You'll see:
   - Meals you can make right now, from your ticked items alone.
   - Your basket -- the cheapest combination of tracked staples that fits your
     budget, with the store each item is cheapest at.
   - Meals you can make after this shop -- additional recipes unlocked by the
     basket, on top of what you already had.

## Data and methodology

- Tracked items: about 28 common grocery staples across protein, carbs, vegetables
  and fruit, and pantry categories, defined in `data/items.yaml` with a
  protein-per-100g value and a purchase unit size (e.g. a 500g pack).
- Recipes: about 32 curated high-protein meals in `data/recipes.json`, each listing
  its ingredients (by item ID) and protein per serving. A recipe is "feasible" when
  every one of its ingredients is in the available item set -- there's no partial
  credit for having most of what a recipe needs.
- "Cheapest": for each tracked item, whichever of Coles or Aldi has the lower
  cached price. The optimizer then ranks all tracked items by protein-grams-per-dollar
  and greedily fills the basket in that order, within budget.
- Aldi coverage is partial, by design: Aldi Australia doesn't sell groceries
  online store-wide -- it publishes a rotating weekly Specials catalogue. This project
  scrapes that Specials page, so many items will show "Coles only this week" rather
  than an Aldi price. That's expected, not a bug.

## Running the tests

```bash
pytest
```

All tests run against fixtures and an in-memory/temp SQLite database -- no network
calls, no live scraping, so they're fast and deterministic. The scraper's live-fetch
functions are exercised manually via `scripts/live_check.py`, not in the automated
suite (see below).

## Checking the live scrapers still work

Site markup changes without notice. To manually confirm Coles/Aldi scraping still
works against the real sites:

```bash
python scripts/live_check.py
```

If a site's markup has changed, the price-parsing functions in `scraper/coles.py` and
`scraper/aldi.py` may need their CSS selector updated -- `scripts/capture_fixture.py`
re-captures a fresh sample page to develop against.

## The analysis notebook

```bash
jupyter notebook notebook/analysis.ipynb
```

Reads `prices.db` if it exists (falling back to the bundled sample data otherwise)
and produces: a protein-per-dollar ranking, a Coles-vs-Aldi price comparison, and (once
the scraper has run more than once) a price-history view per item.
```

- [ ] **Step 5: Write `README.md`**, Part 5 — Project Structure through License:

```markdown
## Project structure

```
protein-budget-planner/
  core/          data models, item/recipe loaders, optimizer, meal matcher
  storage/       SQLite price cache
  scraper/       Coles/Aldi scrapers, price parsing, scrape orchestration
  web/           FastAPI app, HTML templates, static CSS
  notebook/      pandas/Jupyter analysis (generated via build_notebook.py)
  data/          items.yaml, recipes.json -- the static catalogs
  sample_data/   illustrative offline demo prices
  scripts/       live_check.py, capture_fixture.py -- manual dev tools
  tests/         pytest suite (fixtures, no live network calls)
  run.py         entry point
```

## Limitations and ethics

- This project accesses public Coles/Aldi web pages the same way a browser would, at
  low, manual, personal-use frequency -- it is not a commercial scraping operation,
  doesn't bypass any login, and isn't run on a schedule. That said, most retail sites'
  Terms of Service restrict automated access; use this responsibly, for personal
  budgeting only, and expect it to need occasional maintenance if a site's markup
  changes.
- Aldi coverage is limited to its published weekly Specials -- see "Data and
  methodology" above.
- Protein values and unit sizes in `data/items.yaml` are reasonable estimates for
  common product sizes, not pulled from a nutrition database -- treat them as
  indicative, not exact.
- This tool recommends what to buy; it doesn't place any order or interact with
  either retailer's checkout.

## Roadmap ideas

- Expand the tracked item list and recipe catalog.
- Add a third store once a reliable public data source is identified.
- Track price history long enough to show seasonal trends in the notebook.

## License

MIT -- see LICENSE.
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: write project README"
```

---

**Note:** before the commit in Step 6 above, also create `LICENSE` (referenced by the
README) with standard MIT License text, copyright line "Copyright (c) 2026 dhruv", and
include it in the same `git add`/commit.

---

## Task 17: Final End-to-End Verification

**Files:** none created — this task only runs and checks things.

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: every test from Tasks 2-15 passes (models, repos, db, price parsing,
optimizer, meals, coles/aldi scraper parsers, run_scrape, web app, run entrypoint,
sample data, notebook build). If anything fails, fix it before moving on -- don't
treat this task as "probably fine."

- [ ] **Step 2: Verify the offline demo path**

```bash
python sample_data/load_sample_data.py
python run.py
```
Expected: browser opens to `http://localhost:8000`. Enter a budget (e.g. `30`), tick a
couple of pantry items (e.g. Eggs, Cheddar Cheese, Onion), submit. Expected: a results
page showing a "Meals you can make right now" section (should include Cheese Omelette
if you ticked eggs/cheese/onion), a basket under $30, and a "Meals you can make after
this shop" section. Stop the server with Ctrl+C when done.

- [ ] **Step 3: Verify the live scraping path (best effort)**

```bash
python scraper/run_scrape.py
```
Expected: prints `Wrote N price records.` with N > 0. If Coles/Aldi have changed their
markup since Tasks 8/9 were implemented, N may be 0 or low -- that's a real possibility
with live scraping, not necessarily a bug in this codebase. If so, re-run
`scripts/capture_fixture.py`, re-inspect, and update the selectors in `scraper/coles.py`
/ `scraper/aldi.py` as described in those tasks.

- [ ] **Step 4: Re-check the app with live data**

```bash
python run.py
```
Submit the same budget again. Expected: the "Prices last updated" timestamp now shows
a recent time (from Step 3's scrape), not the sample data's fixed timestamp.

- [ ] **Step 5: Final commit**

```bash
git add -A
git status
git commit -m "chore: final verification pass"
```
(If `git status` shows nothing staged, there's nothing to commit -- that's fine, skip
the commit.)

- [ ] **Step 6: Stop here — do not push to GitHub yet**

Per the project owner's explicit instruction, GitHub publishing (repo creation, login,
push) happens in a separate step after they've reviewed the working app locally, not as
part of this plan. See the design spec, section 8, for the publishing plan to follow
when they're ready.
