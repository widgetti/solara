import unittest.mock

import pytest

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


@pytest.mark.parametrize("use_tags", [True, False])
def test_component_vue_basic_with_custom_serializer(use_tags: bool):
    if use_tags:

        @solara._component_vue("component_vue_test.vue", tags={"value": {"to_json": lambda x, w: str(x), "from_json": lambda x, w: int(x)}})
        def ComponentVueTest(value: int, name: str = "World"):
            pass
    else:

        @solara._component_vue("component_vue_test.vue", to_json={"value": lambda x, w: str(x)}, from_json={"value": lambda x, w: int(x)})
        def ComponentVueTest(value: int, name: str = "World"):
            pass

    box, rc = solara.render(ComponentVueTest(value=1))
    widget = box.children[0]
    assert widget.value == 1
    assert widget.name == "World"

    state = widget.get_state()
    assert state["value"] == "1"
    assert state["name"] == "World"

    state["value"] = "2"
    state["name"] = "Universe"
    widget.set_state(state)
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


def test_component_vue_event():
    mock = unittest.mock.Mock()

    @solara._component_vue("component_vue_test.vue")
    def ComponentVueTest(event_foo=None):
        pass

    box, rc = solara.render(ComponentVueTest(event_foo=mock), handle_error=False)
    widget = box.children[0]
    mock.assert_not_called()
    widget._handle_event(None, {"event": "foo", "data": 42}, None)
    mock.assert_called_once_with(42)
    widget._handle_event(None, {"event": "foo", "data": 42}, [b"bar"])
    mock.assert_called_with(42, [b"bar"])

    widget._handle_event(None, {"event": "event_foo", "data": 43}, [b"bar2"])
    mock.assert_called_with(43, [b"bar2"])
