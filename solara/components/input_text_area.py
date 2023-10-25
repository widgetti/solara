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
def InputTextArea(
    label: str,
    value: Union[str, solara.Reactive[str]] = "",
    on_value: Callable[[str], None] = None,
    disabled: bool = False,
    password: bool = False,
    continuous_update: bool = False,
    error: Union[bool, str] = False,
    message: Optional[str] = None,
    **kwargs,
):
    """Free form text input multi-line text-field, useful for larger amounts of text.

    ### Basic example:

    ```solara
    import solara

    text = solara.reactive("Hello world!")
    continuous_update = solara.reactive(True)

    @solara.component
    def Page():
        solara.Checkbox(label="Continuous update", value=continuous_update)
        solara.InputTextArea("Enter some text", value=text, continuous_update=continuous_update.value)
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
        solara.InputTextArea("Enter a passsword", value=password, continuous_update=continuous_update.value, password=True)
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
    text_field = v.Textarea(
        v_model=reactive_value.value,
        on_v_model=on_v_model,
        label=label,
        disabled=disabled,
        #type="password" if password else None,
        error=bool(error),
        messages=messages,
        **kwargs,
    )
    use_change(text_field, set_value_cast, enabled=not continuous_update)
    return text_field
