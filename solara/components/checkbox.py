from typing import Callable, Union

import reacton
import reacton.ipyvuetify as v

import solara


@reacton.value_component(bool)
def Checkbox(
    *,
    label=None,
    value: Union[bool, solara.Reactive[bool]] = True,
    on_value: Callable[[bool], None] = None,
    disabled=False,
    style: str = None,
):
    """A checkbox is a widget that allows the user to toggle a boolean state.

    Basic examples

    ```solara
    import solara

    turbo_boost = solara.reactive(True)

    @solara.component
    def Page():
        checkbox = solara.Checkbox(label="Turbo boost", value=turbo_boost)
        if turbo_boost.value:
            solara.Success("Turbo boost is on")
        else:
            solara.Warning("Turbo boost is off, you might want to turn it on")
    ```


    ## Arguments

     * `label`: The label to display next to the checkbox.
     * `value`: The current value of the checkbox (True or False).
     * `on_value`: A callback that is called when the checkbox is toggled.
     * `disabled`: If True, the checkbox is disabled and cannot be used.
     * `style`: A string of CSS styles to apply to the checkbox.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value
    children = []
    if label is not None:
        children = [label]
    return v.Checkbox(label=label, v_model=reactive_value.value, on_v_model=reactive_value.set, disabled=disabled, style_=style, children=children)
