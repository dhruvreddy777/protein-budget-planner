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
