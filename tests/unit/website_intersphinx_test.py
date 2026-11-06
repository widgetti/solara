from solara.website import intersphinx


def test_committed_inventory_is_up_to_date():
    expected = intersphinx.inventory_body(intersphinx.collect_entries())
    assert intersphinx.read_inventory_body() == expected, "Run: python -m solara.website.intersphinx"


def test_inventory_entries():
    entries = {entry.name: entry for entry in intersphinx.collect_entries()}
    assert entries["solara.Button"] == intersphinx.Entry("solara.Button", "function", "documentation/components/input/button")
    # the full module path points to the same page
    assert entries["solara.components.button.Button"].uri == "documentation/components/input/button"
    # a page that documents more objects links to the heading
    assert entries["solara.InputTextArea"].uri == "documentation/components/input/input#inputtextarea"
    assert entries["solara.lab.Menu"].uri == "documentation/components/lab/menu#menu"
    assert entries["solara.Route"].role == "class"
    # pages without an apidoc call, found by file name
    assert entries["solara.use_effect"].uri == "documentation/api/hooks/use_effect"
