# ProteinBudget Planner — Design Spec

**Date:** 2026-10-18
**Status:** Approved for implementation planning

## 1. Problem & Goal

Given a grocery budget, find the cheapest way to spend it across nearby stores (Coles and
Aldi, Sydney NSW), and suggest high-protein meals that can be made from what was bought.
The app runs entirely on the user's laptop (no deployment/hosting), and the project is
published to GitHub as a portfolio piece for a Master's in Data Science — so it should read
as more than a CRUD web app: it includes a small data-analysis layer (pandas + a notebook)
on top of the live app.

## 2. Non-Goals

- No real-time/production-grade scraping infrastructure (proxy rotation, CAPTCHA solving,
  etc.) — this is a personal, low-frequency, non-commercial tool.
- No coverage guarantee for Aldi's full catalog — Aldi Australia does not publish a full
  priced online grocery range; only its weekly Specials catalogue is scraped. This is a
  known, documented limitation, not a bug.
- No user accounts, no multi-user support, no cloud sync.
- No payment/checkout integration — this only recommends what to buy, it doesn't buy it.

## 3. Architecture

Single Python process, run locally with one command (`python run.py`), which starts a
FastAPI server and opens the browser to `http://localhost:8000`.

```
Scraper (Playwright) -> SQLite (prices.db) -> Optimizer/Meal Matcher -> FastAPI + HTML/JS UI
                               |
                               v
                     pandas + Jupyter notebook  (separate, manual - portfolio artifact)
```

**Components:**

1. **Scraper** (`scraper/`) — Playwright-driven fetchers for Coles and Aldi. Reads the
   item list from `data/items.yaml`, writes normalized price records (store, item_id,
   price, unit, scraped_at) to SQLite. Runs on demand (a "Refresh prices" action), not on
   a schedule.
2. **Storage** (`storage/`) — SQLite wrapper (`prices.db`, gitignored — it's scraped data,
   not source). Append-only price history table, so repeated runs build up a time series
   usable by the notebook.
3. **Optimizer** (`core/optimizer.py`) — Given a budget and the latest cached prices,
   greedily selects items maximizing protein-grams-per-dollar within budget, preferring
   the cheaper store per item.
4. **Meal matcher** (`core/meals.py`) — Given the optimizer's basket, matches against
   `data/recipes.json` (30-40 curated high-protein meals) and ranks feasible meals by
   protein/serving.
5. **Web app** (`web/`) — FastAPI routes + plain HTML/CSS/JS templates (no build step):
   budget input form -> results page (basket, total spend vs. budget, suggested meals,
   data-freshness badge per store).
6. **Analysis notebook** (`notebook/analysis.ipynb`) — separate from the live app; reads
   `prices.db` (or the committed `sample_data/` if no live scrape has run yet) and produces
   EDA: price comparison charts, protein-per-dollar rankings, basket-cost trends over time.

## 4. Data Flow

1. User clicks "Refresh prices" (or app auto-refreshes if cache is older than a configurable
   threshold, e.g. 24h).
2. Scraper visits each configured item's search term on Coles and Aldi Specials, extracts
   price, writes to SQLite with a timestamp. Failures are caught per-item/per-store — one
   failure doesn't abort the whole run.
3. If a scrape attempt fails entirely (site blocked/down/changed), the app falls back to
   the most recent cached row for that store and surfaces a "data from [timestamp]" badge.
4. User submits a budget on the web form.
5. Optimizer reads latest cached prices, builds the best basket under budget.
6. Meal matcher ranks recipes against the basket.
7. Results page renders basket + spend + suggested meals.
8. (Independently, anytime) user opens the notebook to explore accumulated price history.

## 5. Data Scope

**Items** (`data/items.yaml`), ~25-30 staples, each with: id, display name, category,
unit, protein_per_100g, Coles search term, Aldi search term (nullable if not currently in
Specials).

Categories: Protein (chicken breast, eggs, canned tuna, lentils, chickpeas, Greek yogurt,
milk, tofu, beef mince, cottage cheese), Carbs (rice, pasta, bread, oats, potatoes),
Veg/fruit (onion, carrot, frozen mixed veg, banana, apple), Pantry (olive oil, canned
tomatoes, peanut butter).

**Recipes** (`data/recipes.json`), 30-40 entries: id, name, ingredients (item_id + qty),
protein_per_serving, servings, brief method text.

## 6. Error Handling

- Per-item/per-store scrape failure -> logged, skipped, doesn't abort the run.
- Full scrape failure with existing cache -> serve cached data + staleness badge.
- Full scrape failure with no cache at all -> friendly error page, no stack trace, suggests
  retrying later.
- Aldi item absent from current Specials -> shown as "Coles only this week," never silently
  dropped from the item list.
- Budget too low for any valid basket -> message showing the cheapest single tracked item's
  price as a concrete reference point.
- Playwright browser not yet installed -> clear one-time setup instruction surfaced on
  first run failure (`playwright install chromium`).

## 7. Testing

- `pytest` unit tests for the optimizer, meal matcher, and price-parsing/normalization
  logic, run against saved HTML/JSON fixtures — deterministic, no live network calls in
  the default test run.
- `scripts/live_check.py` — a manual, explicitly-invoked script to sanity-check real
  scraping against the live Coles/Aldi sites when desired. Never run in automated tests.
- Notebook is not unit-tested but includes markdown narration for readability.

## 8. Repo, Storage Location & Publishing

- **Local path:** `C:\Users\dhruv\Documents\projects\protein-budget-planner`
- **`.gitignore`:** venv, `__pycache__`, `prices.db` (live scraped cache — not source)
- **`sample_data/`:** a small committed snapshot of prices/items so the notebook and a
  fresh clone produce visible output without first installing Playwright or scraping live
- **README.md:** problem statement, architecture diagram, setup/run instructions,
  screenshots, a data-source & ethics note (personal/educational use, rate-limited,
  respects robots.txt where reasonably possible, not for redistribution), limitations
  (Aldi coverage caveat), license (MIT)
- **GitHub:** new public repo named `protein-budget-planner`, created once the app is
  working and the user has logged into `gh` (deferred by user request — not done during
  initial build).

## 9. Open Items Deferred to Implementation

- Exact greedy algorithm tie-breaking rules for the optimizer (documented in code, tested
  via fixtures).
- Exact list of initial 30-40 recipes (will be authored during implementation, reviewed
  for variety/realism).
