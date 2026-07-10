import ipyvuetify as v
import pytest

import solara
import solara.lab
from solara.util import IPYVUETIFY_V3


def test_tabs_no_children():
    @solara.component
    def Test():
        with solara.lab.Tabs():
            solara.lab.Tab("Tab 1")
            solara.lab.Tab("Tab 2")

    box, rc = solara.render(Test(), handle_error=False)
    assert len(rc.find(v.Tab)) == 2
    assert len(rc.find(v.Tab)) == 2
    assert rc.find(v.Tabs).widget.v_model == 0


@pytest.mark.parametrize("lazy", [True, False])
def test_tabs_basics(lazy):
    @solara.component
    def Test():
        index, set_index = solara.use_state(0)
        with solara.lab.Tabs(value=index, on_value=set_index, lazy=lazy):
            with solara.lab.Tab("Tab 1"):
                solara.SliderInt("Slider 1", value=1)
            with solara.lab.Tab("Tab 2"):
                solara.InputText("Input 2", value="2")

    box, rc = solara.render(Test(), handle_error=False)
    assert len(rc.find(v.Tab)) == 2
    if IPYVUETIFY_V3:
        content_component = v.Window
        item_component = v.WindowItem
    else:
        content_component = v.TabsItems
        item_component = v.TabItem
    assert len(rc.find(content_component)) == 1
    if lazy:
        assert len(rc.find(item_component)) == 2
        assert len(rc.find(v.SkeletonLoader)) == 0
        assert len(rc.find(v.Slider)) == 1
        assert len(rc.find(v.TextField)) == 0
    else:
        assert len(rc.find(item_component)) == 2
        assert len(rc.find(v.SkeletonLoader)) == 0
        assert len(rc.find(v.SkeletonLoader)) == 0
        assert len(rc.find(v.Slider)) == 1
        assert len(rc.find(v.TextField)) == 1
    assert rc.find(v.Tabs).widget.v_model == 0


def test_tabs_props_match_installed_ipyvuetify():
    @solara.component
    def Test():
        with solara.lab.Tabs(background_color="red", slider_color="blue", dark=True, vertical=True, align="center"):
            solara.lab.Tab("Tab", icon_name="mdi-home")

    _, rc = solara.render(Test(), handle_error=False)
    tabs = rc.find(v.Tabs).widget
    icon = rc.find(v.Icon).widget
    if IPYVUETIFY_V3:
        assert tabs.align_tabs == "center"
        assert tabs.direction == "vertical"
        assert tabs.bg_color == "red"
        assert tabs.slider_color == "blue"
        assert tabs.class_ == "v-theme--dark"
        assert icon.start is True
    else:
        assert tabs.centered is True
        assert tabs.vertical is True
        assert tabs.background_color == "red"
        assert rc.find(v.TabsSlider).widget.color == "blue"
        assert icon.left is True
    rc.close()
