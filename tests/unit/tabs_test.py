import ipyvuetify as v
import pytest

import solara
import solara.lab


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
    assert len(rc.find(v.TabsItems)) == 1
    if lazy:
        assert len(rc.find(v.TabItem)) == 2
        assert len(rc.find(v.SkeletonLoader)) == 0
        assert len(rc.find(v.Slider)) == 1
        assert len(rc.find(v.TextField)) == 0
    else:
        assert len(rc.find(v.TabItem)) == 2
        assert len(rc.find(v.SkeletonLoader)) == 0
        assert len(rc.find(v.SkeletonLoader)) == 0
        assert len(rc.find(v.Slider)) == 1
        assert len(rc.find(v.TextField)) == 1
    assert rc.find(v.Tabs).widget.v_model == 0
