import ast
from typing import Any, Callable, Optional, TypeVar, Union, cast, overload

import ipyvue
import ipyvuetify as vw
import reacton
from typing_extensions import Literal

import solara
from solara.alias import rv as v

T = TypeVar("T")


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


@overload
@solara.component
def InputFloat(
    label: str,
    value: float = 0,
    on_value: Optional[Callable[[float], None]] = ...,
    disabled: bool = ...,
    optional: Literal[False] = ...,
    continuous_update: bool = ...,
    hide_details: bool = ...,
    clearable: bool = ...,
) -> reacton.core.ValueElement[vw.TextField, Any]:
    ...


@overload
@solara.component
def InputFloat(
    label: str,
    value: Optional[float] = 0,
    on_value: Optional[Callable[[Optional[float]], None]] = ...,
    disabled: bool = ...,
    optional: Literal[True] = ...,
    continuous_update: bool = ...,
    hide_details: bool = ...,
    clearable: bool = ...,
) -> reacton.core.ValueElement[vw.TextField, Any]:
    ...


@solara.component
def InputFloat(
    label: str,
    value: Optional[float] = 0,
    on_value: Union[None, Callable[[Optional[float]], None], Callable[[float], None]] = None,
    disabled: bool = False,
    optional: bool = False,
    continuous_update: bool = False,
    clearable: bool = False,
):
    """Numeric input.

    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `optional`: Whether the value can be None.
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    * `clearable`: Whether the input can be cleared.

    """
    return _InputNumeric(
        float,
        label=label,
        value=value,
        on_value=on_value,
        disabled=disabled,
        continuous_update=continuous_update,
        clearable=clearable,
        optional=optional,
    )


@overload
@solara.component
def InputInt(
    label: str,
    value: int = 0,
    on_value: Optional[Callable[[int], None]] = ...,
    disabled: bool = ...,
    optional: Literal[False] = ...,
    continuous_update: bool = ...,
    clearable: bool = ...,
) -> reacton.core.ValueElement[vw.TextField, Any]:
    ...


@overload
@solara.component
def InputInt(
    label: str,
    value: Optional[int] = 0,
    on_value: Optional[Callable[[Optional[int]], None]] = ...,
    disabled: bool = ...,
    optional: Literal[True] = ...,
    continuous_update: bool = ...,
    clearable: bool = ...,
) -> reacton.core.ValueElement[vw.TextField, Any]:
    ...


@solara.component
def InputInt(
    label: str,
    value: Optional[int] = 0,
    on_value: Union[None, Callable[[Optional[int]], None], Callable[[int], None]] = None,
    disabled: bool = False,
    optional: bool = False,
    continuous_update: bool = False,
    clearable: bool = False,
):
    """Numeric input.

    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `optional`: Whether the value can be None.
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    * `clearable`: Whether the input can be cleared.
    """
    return _InputNumeric(
        int,
        label=label,
        value=value,
        on_value=on_value,
        disabled=disabled,
        optional=optional,
        continuous_update=continuous_update,
        clearable=clearable,
    )


@solara.component
def _InputNumeric(
    str_to_numeric: Callable[[str], T],
    label: str,
    value: Optional[T],
    on_value: Union[None, Callable[[Optional[T]], None], Callable[[T], None]] = None,
    disabled: bool = False,
    optional: bool = False,
    continuous_update: bool = False,
    clearable: bool = False,
):
    """Numeric input.

    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    """
    error, set_error = solara.use_state(False)
    internal_value, set_internal_value = solara.use_state(cast(Union[str, T, None], str(value) if value is not None else None))

    def parse(value):
        return ast.literal_eval(value.replace(",", "."))

    def on_external_value_change():
        nonlocal internal_value
        # only gets called when initial_or_updated changes
        if isinstance(internal_value, str):
            try:
                numerical_value = ast.literal_eval(internal_value.replace(",", "."))
            except Exception:
                set_internal_value(value)
                # this make sure the current value gets updated directly
                internal_value = str(value)
            else:
                if numerical_value != value:
                    set_internal_value(str(value))
                    # this make sure the current value gets updated directly
                    internal_value = str(value)
        elif internal_value is not None:
            if internal_value != value:
                set_internal_value(value)
                # this make sure the current value gets updated directly
                internal_value = value

    # make sure that if the external value changes, our internal model gets updated
    # but if the internal model is in a different representation
    # (e.g. internal_value='1e2' and internal_value=100) we don't want to change
    # our internal model
    solara.use_memo(on_external_value_change, [value])

    def on_internal_value_change():
        if isinstance(internal_value, str):
            try:
                numerical_value = ast.literal_eval(internal_value.replace(",", "."))
            except Exception:
                return internal_value
            else:
                if numerical_value != value:
                    return value
                else:
                    return internal_value
        elif internal_value is not None:
            if internal_value != value:
                return value
            else:
                return internal_value

    # make sure that out internal value is not out of sync with the value
    # e.g. internal_value='4' and value=4 -> internal_value='4.1' and value=4.1
    # and we are using int, we want to make sure our internal value is '4'
    internal_value = solara.use_memo(on_internal_value_change, [value, internal_value])

    def set_value_cast(value):
        set_internal_value(value)
        if value is None or value == "":
            if optional:
                set_error(False)
                if on_value:
                    on_value(None)  # type: ignore
            else:
                set_error(True)
            return
        try:
            numeric_value = str_to_numeric(parse(value))
        except Exception:
            set_error(True)
        else:
            set_error(False)
            if on_value:
                on_value(numeric_value)

    def on_v_model(value):
        if continuous_update:
            set_value_cast(value)

    if error:
        label += " (invalid)"
    text_field = v.TextField(
        v_model=internal_value,
        on_v_model=on_v_model,
        label=label,
        disabled=disabled,
        # we are not using the numer type, since we cannot validate invalid input
        # see https://stackoverflow.blog/2022/12/26/why-the-number-input-is-the-worst-input/
        # type="number",
        hide_details=True,
        clearable=clearable,
        error=error,
    )
    use_change(text_field, set_value_cast, enabled=not continuous_update)
    return text_field
