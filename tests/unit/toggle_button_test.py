from typing import Optional

import solara


def test_toggle_buttons_single():
    value: Optional[str] = None

    def set(value_):
        nonlocal value
        value = value_

    @solara.component
    def Test():
        with solara.ToggleButtonsSingle("noot", on_value=set) as main:
            solara.Button("Aap", value="aap")
            solara.Button("Noot", value="noot")
            solara.Button("Mies", value="mies")
        return main

    group, rc = solara.render_fixed(Test())
    assert group.v_model == 1
    group.v_model = 2
    assert value == "mies"


def test_toggle_buttons_multiple():
    value: Optional[str] = None

    def set(value_):
        nonlocal value
        value = value_

    @solara.component
    def Test():
        with solara.ToggleButtonsMultiple(["noot"], on_value=set) as main:
            solara.Button("Aap", value="aap")
            solara.Button("Noot", value="noot")
            solara.Button("Mies", value="mies")
        return main

    group, rc = solara.render_fixed(Test())
    assert group.v_model == [1]
    group.v_model = [0, 2]
    assert value is not None
    assert value == ["aap", "mies"]
