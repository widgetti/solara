import pytest
import solara

import solara_html


def test_argument_clashing_with_widget_attribute(tmp_path):
    path = tmp_path / "c.html"
    path.write_text("<template></template>", encoding="utf-8")

    def Component(open=False):
        pass

    with pytest.raises(ValueError, match="'open' clashes"):
        solara_html.component_html(str(path))(Component)


def prop_and_its_setter(x=None, setX=None):
    pass


def props_that_differ_in_case(x=None, X=None):
    pass


def prop_and_event(click=None, event_click=None):
    pass


@pytest.mark.parametrize(
    "Component, first, second, react_name",
    [
        (prop_and_its_setter, "x", "setX", "setX"),
        (props_that_differ_in_case, "x", "X", "setX"),
        (prop_and_event, "click", "event_click", "click"),
    ],
)
def test_arguments_with_the_same_react_prop(tmp_path, Component, first, second, react_name):
    path = tmp_path / "c.html"
    path.write_text("<template></template>", encoding="utf-8")

    with pytest.raises(ValueError, match=f"'{first}' and '{second}' both give the React prop '{react_name}'"):
        solara_html.component_html(str(path))(Component)


@pytest.mark.parametrize("children", [None, []])
def test_children_none_or_empty(tmp_path, children):
    path = tmp_path / "c.html"
    path.write_text("<template><slot></slot></template>", encoding="utf-8")

    @solara_html.component_html(str(path))
    def Html(name="World", children=[]):
        pass

    @solara.component
    def Test():
        return Html(name="Solara", children=children)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert widget.children == []
    assert widget.name == "Solara"
    rc.close()
