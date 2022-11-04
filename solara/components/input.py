from typing import Any, Callable, cast

import ipyvue
import reacton

import solara
from solara.alias import rv as v


def use_change(el: reacton.core.Element, on_value: Callable[[Any], Any], enabled=True):
    """Trigger a callback when a blur events occurs or the enter key is pressed."""
    on_value_ref = solara.use_ref(on_value)
    on_value_ref.current = on_value

    def add_events():
        def on_change(widget, event, data):
            if enabled:
                on_value_ref.current(widget.v_model)

        widget = cast(ipyvue.VueWidget, solara.get_widget(el))
        if enabled:
            widget.on_event("blur", on_change)
            widget.on_event("keyup.enter", on_change)

        def cleanup():
            if enabled:
                widget.on_event("blur", on_change, remove=True)
                widget.on_event("keyup.enter", on_change, remove=True)

        return cleanup

    solara.use_effect(add_events, [enabled])


@solara.component
def InputText(
    label: str,
    value: str = "",
    on_value: Callable[[str], None] = None,
    disabled: bool = False,
    password: bool = False,
    continuous_update: bool = False,
):
    """Free form text input.

    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `password`: Whether the input is a password input (typically shows input text obscured with an asterisk).
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    """

    def set_value_cast(value):
        if on_value is None:
            return
        on_value(str(value))

    def on_v_model(value):
        if continuous_update:
            set_value_cast(value)

    text_field = v.TextField(v_model=value, on_v_model=on_v_model, label=label, disabled=disabled, type="password" if password else None)
    use_change(text_field, set_value_cast, enabled=not continuous_update)
    return text_field


@solara.component
def InputFloat(
    label: str,
    value: float = 0.0,
    on_value: Callable[[float], None] = None,
    disabled: bool = False,
    continuous_update: bool = False,
):
    """Numeric input.

    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    """

    def set_value_cast(value):
        if on_value is None:
            return
        try:
            float_value = float(value)
        except Exception:
            # TODO: maybe we should show an error message here?
            return
        on_value(float_value)

    def on_v_model(value):
        if continuous_update:
            set_value_cast(value)

    text_field = v.TextField(v_model=value, on_v_model=on_v_model, label=label, disabled=disabled, type="number")
    use_change(text_field, set_value_cast, enabled=not continuous_update)
    return text_field
