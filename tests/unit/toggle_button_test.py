from typing import Optional

import solara


def test_toggle_buttons_single():
    value: solara.Reactive[Optional[str]] = solara.reactive(None)

    @solara.component
    def Test():
        with solara.ToggleButtonsSingle("noot", on_value=value.set):
            solara.Button("Aap", value="aap")
            solara.Button("Noot", value="noot")
            solara.Button("Mies", value="mies")
            solara.Button("Nobody", value=None)

    group, rc = solara.render_fixed(Test())
    assert group.v_model == 1
    group.v_model = 2
    assert value.value == "mies"
    group.v_model = 3
    assert value.value is None
    # we don't want it to change the index to None
    assert group.v_model == 3


def test_toggle_buttons_multiple():
    value: solara.Reactive[Optional[str]] = solara.reactive(None)

    @solara.component
    def Test():
        with solara.ToggleButtonsMultiple(["noot"], on_value=value.set):
            solara.Button("Aap", value="aap")
            solara.Button("Noot", value="noot")
            solara.Button("Mies", value="mies")

    group, rc = solara.render_fixed(Test())
    assert group.v_model == [1]
    group.v_model = [0, 2]
    assert value.value is not None
    assert value.value == ["aap", "mies"]
