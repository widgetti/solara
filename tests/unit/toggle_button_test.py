from typing import List, Optional

import solara
from solara.util import IPYVUETIFY_V3


def test_toggle_buttons_single():
    value: solara.Reactive[Optional[str]] = solara.reactive(None)

    @solara.component
    def Test():
        with solara.ToggleButtonsSingle("noot", on_value=value.set):
            solara.Button("Aap", value="aap")
            solara.Button("Noot", value="noot")
            solara.Button("Mies", value="mies")
            solara.Button("Nobody", value=None)

    group, rc = solara.render_fixed(Test(), handle_error=False)
    assert group.v_model == ("noot" if IPYVUETIFY_V3 else 1)
    group.v_model = "mies" if IPYVUETIFY_V3 else 2
    assert value.value == "mies"
    group.v_model = None if IPYVUETIFY_V3 else 3
    assert value.value is None
    assert group.v_model == (None if IPYVUETIFY_V3 else 3)
    rc.close()


def test_toggle_buttons_multiple():
    value: solara.Reactive[Optional[List[str]]] = solara.reactive(None)

    @solara.component
    def Test():
        with solara.ToggleButtonsMultiple(["noot"], on_value=value.set):
            solara.Button("Aap", value="aap")
            solara.Button("Noot", value="noot")
            solara.Button("Mies", value="mies")

    group, rc = solara.render_fixed(Test())
    if IPYVUETIFY_V3:
        assert group.v_model == ["noot"]
        group.v_model = ["aap", "mies"]
    else:
        assert group.v_model == [1]
        group.v_model = [0, 2]
    assert value.value is not None
    assert value.value == ["aap", "mies"]
    rc.close()


def test_toggle_buttons_integer_values():
    value = solara.reactive(20)

    @solara.component
    def Test():
        return solara.ToggleButtonsSingle(value, values=[10, 20, 30])

    group, rc = solara.render_fixed(Test(), handle_error=False)
    assert group.v_model == (20 if IPYVUETIFY_V3 else 1)
    group.v_model = 30 if IPYVUETIFY_V3 else 2
    assert value.value == 30
    rc.close()
