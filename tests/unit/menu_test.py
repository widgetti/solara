import ipyvue
import ipyvuetify as v
import pytest

import solara
from solara.lab.components.menu import ClickMenu, ContextMenu, Menu
from solara.util import IPYVUETIFY_V3


@pytest.mark.parametrize(
    "component, context, use_absolute",
    [(ClickMenu, False, True), (ContextMenu, True, True), (Menu, False, False)],
)
def test_menu_uses_version_specific_template(component, context, use_absolute):
    activator = solara.Button("open")
    element = component(activator=activator, open_value=True, children=[solara.Text("content")])

    _, rc = solara.render(element, handle_error=False)
    widget = rc.find(ipyvue.VueTemplate).widget
    assert (':target="context ? menu_target : undefined"' in widget.template.template) is IPYVUETIFY_V3
    assert widget.show_menu is True
    assert widget.context is context
    assert widget.use_absolute is use_absolute
    assert rc.find(v.Btn).widget.children == ["open"]
    rc.close()
