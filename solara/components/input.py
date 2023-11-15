from typing import Any, Callable, Optional, TypeVar, Union, cast, overload, List, Dict

import ipyvue
import ipyvuetify as vw
import reacton
from typing_extensions import Literal

import solara
from solara.alias import rv as v

T = TypeVar("T")


def use_change(el: reacton.core.Element, on_value: Callable[[Any], Any], enabled=True, update_events=["blur", "keyup.enter"]):
    """Trigger a callback when a blur events occurs or the enter key is pressed."""
    on_value_ref = solara.use_ref(on_value)
    on_value_ref.current = on_value

    def add_events():
        def on_change(widget, event, data):
            if enabled:
                on_value_ref.current(widget.v_model)

        widget = cast(ipyvue.VueWidget, solara.get_widget(el))
        if enabled:
            for event in update_events:
                widget.on_event(event, on_change)

        def cleanup():
            if enabled:
                for event in update_events:
                    widget.on_event(event, on_change, remove=True)

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
    update_events: List[str] = ["blur", "keyup.enter"],
    error: Union[bool, str] = False,
    message: Optional[str] = None,
    classes: List[str] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
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
    * `update_events`: A list of events that should trigger `on_value`. If continuous update is enabled, this will effectively be ignored,
        since updates will happen every change.
    * `error`: If truthy, show the input as having an error (in red). If a string is passed, it will be shown as the error message.
    * `message`: Message to show below the input. If `error` is a string, this will be ignored.
    * `classes`: List of CSS classes to apply to the input.
    * `style`: CSS style to apply to the input.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value
    style_flat = solara.util._flatten_style(style)
    classes_flat = solara.util._combine_classes(classes)

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
        class_=classes_flat,
        style_=style_flat,
    )
    use_change(text_field, set_value_cast, enabled=not continuous_update, update_events=update_events)
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
    classes: List[str] = ...,
    style: Optional[Union[str, Dict[str, str]]] = ...,
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
    classes: List[str] = ...,
    style: Optional[Union[str, Dict[str, str]]] = ...,
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
    classes: List[str] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
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
    * `classes`: List of CSS classes to apply to the input.
    * `style`: CSS style to apply to the input.

    """

    def str_to_float(value: Optional[str]):
        if value:
            try:
                value = value.replace(",", ".")
                return float(value)
            except ValueError:
                raise ValueError("Value must be a number")
        else:
            if optional:
                return None
            else:
                raise ValueError("Value cannot be empty")

    return _InputNumeric(
        str_to_float,
        label=label,
        value=value,
        on_value=on_value,
        disabled=disabled,
        continuous_update=continuous_update,
        clearable=clearable,
        classes=classes,
        style=style,
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
    classes: List[str] = ...,
    style: Optional[Union[str, Dict[str, str]]] = ...,
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
    classes: List[str] = ...,
    style: Optional[Union[str, Dict[str, str]]] = ...,
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
    classes: List[str] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
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
    * `classes`: List of CSS classes to apply to the input.
    * `style`: CSS style to apply to the input.
    """

    def str_to_int(value: Optional[str]):
        if value:
            try:
                return int(value)
            except ValueError:
                raise ValueError("Value must be an integer")
        else:
            if optional:
                return None
            else:
                raise ValueError("Value cannot be empty")

    return _InputNumeric(
        str_to_int,
        label=label,
        value=value,
        on_value=on_value,
        disabled=disabled,
        continuous_update=continuous_update,
        clearable=clearable,
        classes=classes,
        style=style,
    )


def _use_input_type(
    input_value: Union[None, T, solara.Reactive[Optional[T]], solara.Reactive[T]],
    parse: Callable[[Optional[str]], T],
    stringify: Callable[[Optional[T]], str],
    on_value: Union[None, Callable[[Optional[T]], None], Callable[[T], None]] = None,
):
    reactive_value = solara.use_reactive(input_value, on_value)  # type: ignore
    del input_value, on_value
    string_value, set_string_value = solara.use_state(stringify(reactive_value.value) if reactive_value.value is not None else None)
    # Use a ref to make sure sync_back_input_value() does not get a stale string_value
    string_value_ref = solara.use_ref(string_value)
    string_value_ref.current = string_value

    error_message = cast(Union[str, None], None)

    try:
        reactive_value.set(parse(string_value))
    except ValueError as e:
        error_message = str(e.args[0])

    def sync_back_input_value():
        def on_external_value_change(new_value: Optional[T]):
            new_string_value = stringify(new_value)
            try:
                parse(string_value_ref.current)
            except ValueError:
                # String value could be invalid when external value is changed by a different component
                set_string_value(new_string_value)
            else:
                if new_value != parse(string_value_ref.current):
                    set_string_value(new_string_value)

        return reactive_value.subscribe(on_external_value_change)

    solara.use_effect(sync_back_input_value, [reactive_value])

    return string_value, error_message, set_string_value


@solara.component
def _InputNumeric(
    str_to_numeric: Callable[[Optional[str]], T],
    label: str,
    value: Union[None, T, solara.Reactive[Optional[T]], solara.Reactive[T]],
    on_value: Union[None, Callable[[Optional[T]], None], Callable[[T], None]] = None,
    disabled: bool = False,
    continuous_update: bool = False,
    clearable: bool = False,
    classes: List[str] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
):
    """Numeric input.

    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    * `classes`: List of CSS classes to apply to the input.
    * `style`: CSS style to apply to the input.
    """
    style_flat = solara.util._flatten_style(style)
    classes_flat = solara.util._combine_classes(classes)

    internal_value, error, set_value_cast = _use_input_type(
        value,
        str_to_numeric,
        str,
        on_value,
    )

    def on_v_model(value):
        if continuous_update:
            set_value_cast(value)

    if error:
        label += f" ({error})"
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
        error=bool(error),
        class_=classes_flat,
        style_=style_flat,
    )
    use_change(text_field, set_value_cast, enabled=not continuous_update)
    return text_field
