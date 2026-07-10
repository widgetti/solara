from unittest.mock import MagicMock

import ipyvuetify as vw

import solara
from solara.components.cross_filter import Select as CrossFilterSelectWidget
from solara.util import IPYVUETIFY_V3


def test_select():
    """
    test select widget
    """
    disabled = None
    on_value = MagicMock()
    on_value_multiple = MagicMock()

    @solara.component
    def Test():
        nonlocal disabled
        disabled = solara.use_reactive(False)
        solara.Select(label="single", values=["test0", "test1", "test2"], on_value=on_value, disabled=disabled.value, dense=True)
        solara.SelectMultiple(
            label="multiple", values=[], all_values=["test0", "test1", "test2"], on_value=on_value_multiple, disabled=disabled.value, dense=True
        )

    _, rc = solara.render(Test(), handle_error=False)
    select = rc.find(vw.Select, label="single").widget
    select_multi = rc.find(vw.Select, label="multiple").widget

    # init
    assert not select.disabled
    assert not select_multi.disabled
    if IPYVUETIFY_V3:
        assert select.density == "compact"
        assert select_multi.density == "compact"
    else:
        assert select.dense is True
        assert select_multi.dense is True

    assert select.v_model is None
    assert select_multi.v_model == []

    # set v_model
    select.v_model = "test0"
    assert on_value.call_count == 1
    assert on_value.call_args[0][0] == "test0"

    select_multi.v_model = ["test0", "test1"]
    assert on_value_multiple.call_count == 1
    assert on_value_multiple.call_args[0][0] == ["test0", "test1"]

    # test disable
    assert disabled is not None
    disabled.set(True)
    assert len(rc.find(vw.Select, disabled=True).widgets) == 2

    rc.close()


def test_cross_filter_select_uses_version_specific_template():
    select = CrossFilterSelectWidget()
    marker = 'v-slot:item="{ props, item }"'
    assert (marker in select.template.template) is IPYVUETIFY_V3
