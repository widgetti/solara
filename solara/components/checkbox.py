from typing import Callable

import reacton.ipyvuetify as v

import solara


@solara.component
def Checkbox(
    *,
    label=None,
    value=True,
    on_value: Callable[[bool], None],
    disabled=False,
    style: str = None,
):
    """A checkbox is a widget that allows the user to toggle a boolean state.

    ## Arguments

     * `label`: The label to display next to the checkbox.
     * `value`: The current value of the checkbox (True or False).
     * `on_value`: A callback that is called when the checkbox is toggled.
     * `disabled`: If True, the checkbox is disabled and cannot be used.
     * `style`: A string of CSS styles to apply to the checkbox.
    """
    children = []
    if label is not None:
        children = [label]
    return v.Checkbox(label=label, v_model=value, on_v_model=on_value, disabled=disabled, style_=style, children=children)
