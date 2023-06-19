import unittest.mock

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


def test_component_vue_callback():
    mock = unittest.mock.Mock()

    @solara._component_vue("component_vue_test.vue")
    def ComponentVueTest(value: int, on_value=None):
        pass

    box, rc = solara.render(ComponentVueTest(value=1, on_value=mock))
    widget = box.children[0]
    assert widget.value == 1
    mock.assert_not_called()
    widget.value = 2
    mock.assert_called_once_with(2)
    widget.value = 3
    mock.assert_called_with(3)
