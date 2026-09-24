import unittest.mock

import ipywidgets as widgets
import pytest

import solara
from solara.components.component_widget import widget_from_signature
from solara.components.html_component_assets import get_component_asset


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


def test_widget_from_signature_uses_renderer_event_prefix():
    mock = unittest.mock.Mock()

    def Component(event_ping=None):
        pass

    Widget = widget_from_signature("HTMLTestWidget", widgets.Widget, Component, "html_", {}, {}, {})
    widget = Widget(_event_callbacks={"ping": mock})

    widget.html_ping({"ok": True})

    mock.assert_called_once_with({"ok": True})
    assert hasattr(widget, "html_event_ping")
    assert not hasattr(widget, "vue_ping")


def test_component_html_python_widget(tmp_path):
    component_file = tmp_path / "component.html"
    component_file.write_text(
        '<template><output data-solara-text="value"></output></template>'
        "<style>:host { color: red; }</style>"
        '<script type="module">export function mount() {}</script>',
        encoding="utf-8",
    )
    callback = unittest.mock.Mock()

    @solara.component_html(str(component_file))
    def Component(value="initial", on_value=None, event_ping=None):
        pass

    box, rc = solara.render(Component(value="hello", on_value=callback, event_ping=callback))
    try:
        widget = box.children[0]
        assert widget.template == '<output data-solara-text="value"></output>'
        assert widget.value == "hello"
        assert widget.prop_names == ["value"]
        assert widget.event_names == ["ping"]
        assert widget.css_asset.endswith(".css")
        assert widget.script_asset.endswith(".js")
        css_asset = get_component_asset(widget.css_asset)
        assert css_asset is not None
        assert css_asset[0] == ":host { color: red; }"
        assert widget._model_module == "solara-html"
        assert widget._model_module_version == "0.1.0"
        widget.value = "updated"
        callback.assert_called_once_with("updated")
        widget._handle_html_event(widget, {"type": "event", "name": "ping", "data": 42}, None)
        assert callback.call_args_list == [unittest.mock.call("updated"), unittest.mock.call(42)]
        widget._handle_html_event(widget, {"type": "event", "name": "unknown", "data": 3}, None)
        assert callback.call_count == 2
    finally:
        rc.close()


def test_component_html_rejects_reserved_argument(tmp_path):
    component_file = tmp_path / "component.html"
    component_file.write_text("<template><p>Hello</p></template>", encoding="utf-8")

    with pytest.raises(ValueError, match="reserved HTML component argument"):

        @solara.component_html(str(component_file))
        def Component(template: str):
            pass


def test_component_html_accepts_positional_event_argument(tmp_path):
    component_file = tmp_path / "component.html"
    component_file.write_text('<template><p data-solara-text="value"></p></template>', encoding="utf-8")
    callback = unittest.mock.Mock()

    @solara.component_html(str(component_file))
    def Component(value, event_ping):
        pass

    box, rc = solara.render(Component("hello", callback))
    try:
        widget = box.children[0]
        assert widget.value == "hello"
        widget._handle_html_event(widget, {"type": "event", "name": "ping", "data": 1}, None)
        callback.assert_called_once_with(1)
    finally:
        rc.close()


def test_component_vue_esm_argument_validation():
    import ipyvue

    with pytest.raises(TypeError, match="either vue_path or esm_module"):
        solara.component_vue()

    with pytest.raises(TypeError, match="either vue_path or esm_module"):
        solara.component_vue("component_vue_test.vue", esm_module="my-components")

    if not hasattr(ipyvue, "define_module"):
        with pytest.raises(RuntimeError, match="ES module support"):
            solara.component_vue(esm_module="my-components")
