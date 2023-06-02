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
    value: Union[str, solara.Reactive[str]] = "",
    on_value: Callable[[str], None] = None,
    disabled: bool = False,
    password: bool = False,
    continuous_update: bool = False,
    error: Union[bool, str] = False,
    message: Optional[str] = None,
):
    """Free form text input.

    ### Basic example:

    ```solara
    import solara

    text = solara.reactive("Hello world!")
    continuous_update = solara.reactive(True)

    @solara.component
    def Page():
        solara.Checkbox(label="Continuous update", value=continuous_update)
        solara.InputText("Enter some text", value=text, continuous_update=continuous_update.value)
        with solara.Row():
            solara.Button("Clear", on_click=lambda: text.set(""))
            solara.Button("Reset", on_click=lambda: text.set("Hello world"))
        solara.Markdown(f"**You entered**: {text.value}")
    ```

    ### Password input:

    This will not show the entered text.

    ```solara
    import solara

    password = solara.reactive("Super secret")
    continuous_update = solara.reactive(True)

    @solara.component
    def Page():
        solara.Checkbox(label="Continuous update", value=continuous_update)
        solara.InputText("Enter a passsword", value=password, continuous_update=continuous_update.value, password=True)
        with solara.Row():
            solara.Button("Clear", on_click=lambda: password.set(""))
            solara.Button("Reset", on_click=lambda: password.set("Super secret"))
        solara.Markdown(f"**You entered**: {password.value}")
    ```


    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `password`: Whether the input is a password input (typically shows input text obscured with an asterisk).
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    * `error`: If truthy, show the input as having an error (in red). If a string is passed, it will be shown as the error message.
    * `message`: Message to show below the input. If `error` is a string, this will be ignored.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value

    def set_value_cast(value):
        reactive_value.value = str(value)

    def on_v_model(value):
        if continuous_update:
            set_value_cast(value)

    messages = []
    if error and isinstance(error, str):
        messages.append(error)
    elif message:
        messages.append(message)
    text_field = v.TextField(
        v_model=reactive_value.value,
        on_v_model=on_v_model,
        label=label,
        disabled=disabled,
        type="password" if password else None,
        error=bool(error),
        messages=messages,
    )
    use_change(text_field, set_value_cast, enabled=not continuous_update)
    return text_field


@overload
@solara.component
def InputFloat(
    label: str,
    value: Union[float, solara.Reactive[float]] = 0,
    on_value: Optional[Callable[[float], None]] = ...,
    disabled: bool = ...,
    optional: Literal[False] = ...,
    continuous_update: bool = ...,
    clearable: bool = ...,
) -> reacton.core.ValueElement[vw.TextField, Any]:
    ...


@overload
@solara.component
def InputFloat(
    label: str,
    value: Union[Optional[float], solara.Reactive[Optional[float]]] = 0,
    on_value: Optional[Callable[[Optional[float]], None]] = ...,
    disabled: bool = ...,
    optional: Literal[True] = ...,
    continuous_update: bool = ...,
    clearable: bool = ...,
) -> reacton.core.ValueElement[vw.TextField, Any]:
    ...


@solara.component
def InputFloat(
    label: str,
    value: Union[None, float, solara.Reactive[float], solara.Reactive[Optional[float]]] = 0,
    on_value: Union[None, Callable[[Optional[float]], None], Callable[[float], None]] = None,
    disabled: bool = False,
    optional: bool = False,
    continuous_update: bool = False,
    clearable: bool = False,
):
    """Numeric input (floats).

    Basic example:

    ```solara
    import solara

    float_value = solara.reactive(42.0)
    continuous_update = solara.reactive(True)

    @solara.component
    def Page():
        solara.Checkbox(label="Continuous update", value=continuous_update)
        solara.InputFloat("Enter a float number", value=float_value, continuous_update=continuous_update.value)
        with solara.Row():
            solara.Button("Clear", on_click=lambda: float_value.set(42.0))
        solara.Markdown(f"**You entered**: {float_value.value}")
    ```


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
    value: Union[int, solara.Reactive[int]] = 0,
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
    value: Union[Optional[int], solara.Reactive[Optional[int]]] = 0,
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
    value: Union[None, int, solara.Reactive[int], solara.Reactive[Optional[int]]] = 0,
    on_value: Union[None, Callable[[Optional[int]], None], Callable[[int], None]] = None,
    disabled: bool = False,
    optional: bool = False,
    continuous_update: bool = False,
    clearable: bool = False,
):
    """Numeric input (integers).

    Basic example:

    ```solara
    import solara

    int_value = solara.reactive(42)
    continuous_update = solara.reactive(True)

    @solara.component
    def Page():
        solara.Checkbox(label="Continuous update", value=continuous_update)
        solara.InputInt("Enter an integer number", value=int_value, continuous_update=continuous_update.value)
        with solara.Row():
            solara.Button("Clear", on_click=lambda: int_value.set(42))
        solara.Markdown(f"**You entered**: {int_value.value}")
    ```

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


def _use_input_numeric(
    str_to_numeric: Callable[[str], T],
    value: Union[None, T, solara.Reactive[Optional[T]], solara.Reactive[T]],
    on_value: Union[None, Callable[[Optional[T]], None], Callable[[T], None]] = None,
    optional: bool = False,
):
    # TODO: make this more type safe
    reactive_value = solara.use_reactive(value, on_value)  # type: ignore
    del value, on_value

    error, set_error = solara.use_state(False)
    internal_value, set_internal_value = solara.use_state(cast(Union[str, T, None], str(reactive_value.value) if reactive_value.value is not None else None))

    def parse(value):
        return ast.literal_eval(value.replace(",", "."))

    def on_external_value_change():
        nonlocal internal_value
        value = reactive_value.value
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
        elif internal_value is None:
            set_internal_value(value)
            # this make sure the current value gets updated directly
            internal_value = value

    # make sure that if the external value changes, our internal model gets updated
    # but if the internal model is in a different representation
    # (e.g. internal_value='1e2' and internal_value=100) we don't want to change
    # our internal model
    solara.use_memo(on_external_value_change, [reactive_value.value])

    def internal_value_check_type():
        if isinstance(internal_value, str):
            try:
                numerical_proper_type = str_to_numeric(parse(internal_value))
                numerical = parse(internal_value)
            except Exception:
                return internal_value
            else:
                if numerical_proper_type != numerical:
                    return str(numerical_proper_type)
                else:
                    return internal_value
        else:
            return internal_value

    # make sure that when internal_value="1.1", but str_to_numeric=int
    # internal value becomes "1"
    internal_value = solara.use_memo(internal_value_check_type, [internal_value])

    def set_value_cast(value):
        set_internal_value(value)
        if value is None or value == "":
            if optional:
                set_error(False)
                reactive_value.set(None)  # type: ignore
            else:
                set_error(True)
            return
        try:
            numeric_value = str_to_numeric(parse(value))
        except Exception:
            set_error(True)
        else:
            set_error(False)
            reactive_value.set(numeric_value)

    return internal_value, set_value_cast, error


@solara.component
def _InputNumeric(
    str_to_numeric: Callable[[str], T],
    label: str,
    value: Union[None, T, solara.Reactive[Optional[T]], solara.Reactive[T]],
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

    internal_value, set_value_cast, error = _use_input_numeric(str_to_numeric, value, on_value, optional)

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
        # we are not using the number type, since we cannot validate invalid input
        # see https://stackoverflow.blog/2022/12/26/why-the-number-input-is-the-worst-input/
        # type="number",
        hide_details=True,
        clearable=clearable,
        error=error,
    )
    use_change(text_field, set_value_cast, enabled=not continuous_update)
    return text_field
