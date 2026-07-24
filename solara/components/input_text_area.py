from typing import Callable, Optional, Union, List
from .input import use_change
import solara
from solara.alias import rv as v


@solara.component
def InputTextArea(
    label: str,
    value: Union[str, solara.Reactive[str]] = "",
    on_value: Callable[[str], None] = None,
    disabled: bool = False,
    continuous_update: bool = False,
    update_events: List[str] = ["focusout"],
    error: Union[bool, str] = False,
    message: Optional[str] = None,
    auto_grow: bool = True,
    rows: int = 5,
    dense: bool = False,
    hide_details: Union[str, bool] = "auto",
    placeholder: Optional[str] = None,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
):
    r"""Free form text area input.

    ### Basic example:

    ```solara
    import solara

    text = solara.reactive("Hello\nWorld\n!!!")
    continuous_update = solara.reactive(True)

    @solara.component
    def Page():
        solara.Checkbox(label="Continuous update", value=continuous_update)
        solara.InputTextArea("Enter some text", value=text, continuous_update=continuous_update.value)
        with solara.Row():
            solara.Button("Clear", on_click=lambda: text.set(""))
            solara.Button("Reset", on_click=lambda: text.set("Hello\nWorld\n!!!"))
        solara.Markdown(f"**You entered**: {text.value}")
    ```


    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently entered value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the input is disabled.
    * `continuous_update`: Whether to call the `on_value` callback on every change or only when the input loses focus or the enter key is pressed.
    * `update_events`: A list of events that should trigger `on_value`. If continuous update is enabled, this will effectively be ignored,
        since updates will happen every change.
    * `auto_grow`: Whether the text area auto grows with more text.
    * `rows`: Number of empty rows to display.
    * `error`: If truthy, show the input as having an error (in red). If a string is passed, it will be shown as the error message.
    * `message`: Message to show below the input. If `error` is a string, this will be ignored.
    * `classes`: List of CSS classes to apply to the input.
    * `style`: CSS style to apply to the input.
    * `dense`: Reduces the input height.
    * `hide_details`: Hides hint and validation errors. When set to 'auto', messages will be rendered only if there's a message (hint, error message, counter value etc) to display.
    * `placeholder`: Sets the input's placeholder text.
    * `prefix`: Displays prefix text.
    * `suffix`: Displays suffix text.
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
    text_area = v.Textarea(
        v_model=reactive_value.value,
        on_v_model=on_v_model,
        label=label,
        disabled=disabled,
        error=bool(error),
        messages=messages,
        solo=True,
        hide_details=hide_details,
        outlined=True,
        rows=rows,
        auto_grow=auto_grow,
        dense=dense,
        placeholder=placeholder if placeholder is not None else "",
        prefix=prefix if prefix is not None else "",
        suffix=suffix if suffix is not None else "",
    )
    use_change(text_area, set_value_cast, enabled=not continuous_update, update_events=update_events)
    return text_area
