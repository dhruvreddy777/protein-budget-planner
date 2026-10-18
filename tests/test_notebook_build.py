from notebook.build_notebook import build


def test_notebook_has_expected_structure():
    nb = build()
    assert len(nb["cells"]) == 9
    assert nb["cells"][0]["cell_type"] == "markdown"
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) == 5
