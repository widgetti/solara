import datetime as dt
from typing import Callable, Dict, List, Optional, Union

import solara
import solara.lab
from solara.lab.components.input_date import use_close_menu
from solara.components.input import _use_input_type


@solara.component
def InputTime(
    value: Union[solara.Reactive[Optional[dt.time]], Optional[dt.time]],
    on_value: Optional[Callable[[Optional[dt.time]], None]] = None,
    label: str = "Pick a time",
    children: List[solara.Element] = [],
    open_value: Union[solara.Reactive[bool], bool] = False,
    on_open_value: Optional[Callable[[bool], None]] = None,
    optional: bool = False,
    twelve_hour_clock: bool = False,
    use_seconds: bool = False,
    allowed_minutes: Optional[List[int]] = None,
    style: Optional[Union[str, Dict[str, str]]] = None,
    classes: Optional[List[str]] = None,
):
    """
    Show a textfield, which when clicked, opens a timepicker. The input time should be of type `datetime.time`.

    ## Basic Example

    ```solara {pycafe-link}
    import solara
    import solara.lab
    import datetime as dt


    @solara.component
    def Page():
        time = solara.use_reactive(dt.time(12, 0))

        solara.lab.InputTime(time, allowed_minutes=[0, 15, 30, 45])
        solara.Text(str(time.value))
    ```

    ## Arguments

    * value: Reactive variable of type `datetime.time`, or `None`. This time is selected the first time the component is rendered.
    * on_value: a callback function for when value changes. The callback function receives the new value as an argument.
    * label: Text used to label the text field that triggers the timepicker.
    * children: List of Elements to be rendered under the timepicker. If empty, a close button is rendered.
    * open_value: Controls and communicates the state of the timepicker. If True, the timepicker is open. If False, the timepicker is closed.
    Intended to be used in conjunction with a custom set of controls to close the timepicker.
    * on_open_value: a callback function for when open_value changes. Also receives the new value as an argument.
    * optional: Determines whether to show an error when value is `None`. If `True`, no error is shown.
    * twelve_hour_clock: If `True`, the timepicker will display in 12-hour format. If `False`, the timepicker will display in 24-hour format.
    * use_seconds: If `True`, the timepicker will allow input of seconds.
    * allowed_minutes: List of allowed minutes for the timepicker. Restricts the input to specific minute intervals.
    * style: CSS style to apply to the text field. Either a string or a dictionary of CSS properties (i.e. `{"property": "value"}`).
    * classes: List of CSS classes to apply to the text field.
    """
    time_format_internal = f"%H:%M{':%S' if use_seconds else ''}"
    time_format_display = f"%H:%M{':%S' if use_seconds else ''}"
    if twelve_hour_clock:
        time_format_display = f"%I:%M{':%S' if use_seconds else ''} %p"
    value_reactive = solara.use_reactive(value, on_value)  # type: ignore
    del value, on_value
    timepicker_is_open = solara.use_reactive(open_value, on_open_value)  # type: ignore
    del open_value, on_open_value

    def set_time_typed_cast(value: Optional[str]):
        if value:
            try:
                time_value = dt.datetime.strptime(value, time_format_display).time()
                return time_value
            except ValueError:
                raise ValueError(f"Time {value} does not match format {time_format_display.replace('%', '')}")
        elif optional:
            return None
        else:
            raise ValueError("Time cannot be empty")

    def time_to_str(time: Optional[dt.time]) -> str:
        if time is not None:
            return time.strftime(time_format_display)
        return ""

    def set_time_cast(new_value: Optional[str]):
        if new_value:
            time_value = dt.datetime.strptime(new_value, time_format_internal).time()
            value_reactive.value = time_value

    def standard_strfy(time: Optional[dt.time]):
        if time is None:
            return None
        else:
            return time.strftime(time_format_internal)

    time_standard_str = standard_strfy(value_reactive.value)

    style_flat = solara.util._flatten_style(style)

    internal_value, error_message, set_value_cast = _use_input_type(value_reactive, set_time_typed_cast, time_to_str)

    if error_message:
        label += f" ({error_message})"
    input = solara.v.TextField(
        label=label,
        v_model=internal_value,
        on_v_model=set_value_cast,
        append_icon="mdi-clock",
        error=bool(error_message),
        style_="min-width: 290px;" + style_flat,
        class_=", ".join(classes) if classes else "",
    )

    use_close_menu(input, timepicker_is_open)

    with solara.lab.Menu(
        activator=input,
        close_on_content_click=False,
        open_value=timepicker_is_open,
        use_activator_width=False,
    ):
        with solara.v.TimePicker(
            ampm_in_title=twelve_hour_clock,
            v_model=time_standard_str,
            on_v_model=set_time_cast,
            format="24hr" if not twelve_hour_clock else "ampm",
            allowed_minutes=allowed_minutes,
            use_seconds=use_seconds,
            style_="width: 100%;",
        ):
            if len(children) > 0:
                solara.display(*children)
