import solara


def test_component_vue_basic():
    @solara._component_vue("component_vue_test.vue")
    def ComponentVueTest(value: int, name: str = "World"):
        pass

    box, rc = solara.render(ComponentVueTest(value=1))
    widget = box.children[0]
    assert widget.value == 1
    assert widget.name == "World"
    rc.render(ComponentVueTest(value=2, name="Universe"))
    assert widget.value == 2
    assert widget.name == "Universe"
