"""FastAPI web app: a budget + pantry-checklist form, and a results page showing the
cheapest basket, meals makeable right now, and meals the basket would unlock."""
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, Form, HTTPException, Request
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


def nicedate(iso: str) -> str:
    """Formats an ISO timestamp like '2026-10-18T09:00:00+00:00' as '18 Oct 2026, 9:00 am'."""
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso
    return f"{dt.day} {dt:%b %Y}, {dt.hour % 12 or 12}:{dt:%M} {'am' if dt.hour < 12 else 'pm'}"


templates.env.filters["nicedate"] = nicedate


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    items = load_items()
    return templates.TemplateResponse(request, "index.html", {"request": request, "items": items, "recipe_count": len(load_recipes())})


MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


@app.get("/recipes", response_class=HTMLResponse)
def recipes_index(request: Request):
    recipes = sorted(load_recipes(), key=lambda r: r.protein_per_serving, reverse=True)
    return templates.TemplateResponse(request, "recipes.html", {
        "request": request, "recipes": recipes, "items": load_items(), "meal_types": MEAL_TYPES,
    })


@app.get("/recipes/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(request: Request, recipe_id: str):
    recipes = load_recipes()
    recipe = next((r for r in recipes if r.id == recipe_id), None)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    # Suggest others that share the main protein (first ingredient), then fill by meal type
    related = [r for r in recipes if r.id != recipe.id and r.ingredients[0] == recipe.ingredients[0]]
    related += [r for r in recipes if r.id != recipe.id and r.meal_type == recipe.meal_type and r not in related]
    return templates.TemplateResponse(request, "recipe_detail.html", {
        "request": request, "recipe": recipe, "items": load_items(), "related": related[:3],
    })


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
        return templates.TemplateResponse(request, "results.html", context)

    basket = build_basket(items, latest_prices, budget, have_ids=have_ids, recipes=recipes)

    if not basket.entries:
        cheapest = cheapest_single_item_price(items, latest_prices, exclude=have_ids)
        context["error"] = (
            f"The cheapest tracked item currently costs ${cheapest:.2f} - try a higher budget."
            if cheapest else "No items currently have a price. Try running the scraper again."
        )
        return templates.TemplateResponse(request, "results.html", context)

    combined_ids = basket.item_ids | have_ids
    shopping_meals = [
        m for m in suggest_meals(recipes, combined_ids, top_n=len(recipes))
        if m.id not in {p.id for p in pantry_meals}
    ]

    context["basket"] = basket
    context["recipe_names"] = {r.id: r.name for r in recipes}
    context["shopping_meals"] = shopping_meals
    return templates.TemplateResponse(request, "results.html", context)
