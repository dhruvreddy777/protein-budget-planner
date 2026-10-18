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
    assert result.item_ids == set(["eggs"])
