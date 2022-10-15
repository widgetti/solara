from typing import Callable

import solara
from solara.alias import rv as v


@solara.component
def InputText(
    label: str,
    value: str = "",
    on_value: Callable[[str], None] = None,
):
    """Free form text input.

    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `thumb_label`: Show a thumb label when sliding (True), always ("always"), or never (False).
    """

    def set_value_cast(value):
        if on_value is None:
            return
        on_value(str(value))

    return v.TextField(v_model=value, on_v_model=set_value_cast, label=label)
