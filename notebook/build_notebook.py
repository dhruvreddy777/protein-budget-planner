"""Generates notebook/analysis.ipynb. Run this whenever you want to (re)create the
notebook from its source cells below, rather than hand-editing raw ipynb JSON.

Usage: python notebook/build_notebook.py
"""
from pathlib import Path

import nbformat as nbf

OUT_PATH = Path(__file__).resolve().parent / "analysis.ipynb"


def build():
    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(
            "# ProteinBudget Planner - Price & Protein-Value Analysis\n\n"
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
            "cols = ['name', 'store', 'price', 'protein_per_unit', 'protein_per_dollar']\n"
            "ranked = merged[cols].sort_values('protein_per_dollar', ascending=False)\n"
            "ranked.head(10)"
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
