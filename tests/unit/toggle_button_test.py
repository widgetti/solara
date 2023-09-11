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

    group, rc = solara.render_fixed(Test())
    assert group.v_model == 1
    group.v_model = 2
    assert value.value == "mies"


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
