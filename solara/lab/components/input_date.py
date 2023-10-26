import datetime as dt
from typing import Callable, Dict, List, Optional, Tuple, Union, cast

import ipyvue
import reacton

import solara
import solara.lab
from solara.components.input import _use_input_type


def use_close_menu(el: reacton.core.Element, is_open: solara.Reactive[bool]):
    is_open_ref = solara.use_ref(is_open)
    is_open_ref.current = is_open

    def monitor_events():
        def close_menu(*ignore_args):
            is_open_ref.current.set(False)

        widget = cast(ipyvue.VueWidget, solara.get_widget(el))
        widget.on_event("keyup.enter", close_menu)
        widget.on_event("keydown.tab", close_menu)

        def cleanup():
            widget.on_event("keyup.enter", close_menu, remove=True)
            widget.on_event("keydown.tab", close_menu, remove=True)

        return cleanup

    solara.use_effect(monitor_events, [])


@solara.component
def InputDate(
    value: Union[solara.Reactive[Optional[dt.date]], Optional[dt.date]],
    on_value: Optional[Callable[[Optional[dt.date]], None]] = None,
    label: str = "Pick a date",
    children: List[solara.Element] = [],
    open_value: Union[solara.Reactive[bool], bool] = False,
    on_open_value: Optional[Callable[[bool], None]] = None,
    optional: bool = False,
    date_format: str = "%Y/%m/%d",
    first_day_of_the_week: int = 1,
    style: Optional[Union[str, Dict[str, str]]] = None,
    classes: Optional[List[str]] = None,
):
    """
    Show a textfield, which when clicked, opens a datepicker. The input date should be a reactive variable of type `datetime.date`.

    ## Basic Example

    ```solara
    import solara
    import solara.lab as lab


    @solara.component
    def Page():
        date = solara.use_reactive(None)
        range_is_open = solara.use_reactive(False)

        with solara.Column():
            lab.InputDate(
                date,
                open=range_is_open,
            )
            solara.Text(str(date.value))
    ```

    ## Arguments

    * value: Reactive variable of type `datetime.date`, or `None`. This date is selected the first time the component is rendered.
    * label: Text used to label the text field that triggers the datepicker.
    * children: List of Elements to be rendered under the calendar. If empty, a close button is rendered.
    * open: Controls and communicates the state of the datepicker. If True, the datepicker is open. If False, the datepicker is closed.
    Intended to be used in conjunction with a custom set of controls to close the datepicker.
    * date_format: Sets the format of the date displayed in the text field. Defaults to `"%Y/%m/%d"`. For more information, see
    <a href="https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes" target="_blank">here</a>.
    * first_day_of_the_week: Sets the first day of the week, as an `int` starting count from Sunday (`=0`). Defaults to `1`, which is Monday.
    """

    def set_date_typed_cast(value: Optional[str]):
        if value:
            try:
                date_value = dt.datetime.strptime(value, date_format).date()
                return date_value
            except ValueError:
                raise ValueError(f"Date {value} does not match format {date_format.replace('%', '')}")
        elif optional:
            return None
        else:
            raise ValueError("Date cannot be empty")

    def date_to_str(date: Optional[dt.date]) -> str:
        if date is not None:
            return date.strftime(date_format)
        return ""

    def set_date_cast(new_value: Optional[str]):
        if new_value:
            date_value = dt.datetime.strptime(new_value, "%Y-%m-%d").date()
            value_reactive.value = date_value

    def standard_strfy(date: Optional[dt.date]):
        if date is None:
            return None
        else:
            return date.strftime("%Y-%m-%d")

    value_reactive = solara.use_reactive(value)
    del value
    date_standard_str = standard_strfy(value_reactive.value)

    datepicker_is_open = solara.use_reactive(open_value, on_open_value)  # type: ignore
    del open_value, on_open_value

    style_flat = solara.util._flatten_style(style)

    internal_value, error_message, set_value_cast = _use_input_type(value_reactive, set_date_typed_cast, date_to_str, on_value)

    if error_message:
        label += f" ({error_message})"
    input = solara.v.TextField(
        label=label,
        v_model=internal_value,
        on_v_model=set_value_cast,
        append_icon="mdi-calendar",
        error=bool(error_message),
        style_=style_flat,
        class_=", ".join(classes) if classes else "",
    )

    use_close_menu(input, datepicker_is_open)

    with solara.lab.Menu(
        activator=input,
        close_on_content_click=False,
        open_value=datepicker_is_open,
    ):
        with solara.v.DatePicker(
            v_model=date_standard_str,
            on_v_model=set_date_cast,
            first_day_of_week=first_day_of_the_week,
            style_="width: 100%;",
        ):
            if len(children) > 0:
                solara.display(*children)
            else:
                with solara.Row(justify="end", style="width: 100%"):
                    solara.Button("close", color="primary", on_click=lambda: datepicker_is_open.set(False))


@solara.component
def InputDateRange(
    value: Union[solara.Reactive[Tuple[Optional[dt.date], Optional[dt.date]]], Tuple[Optional[dt.date], Optional[dt.date]]],
    on_value: Optional[Callable[[Optional[Tuple[Optional[dt.date], Optional[dt.date]]]], None]] = None,
    label: str = "Select dates",
    children: List[solara.Element] = [],
    open_value: Union[solara.Reactive[bool], bool] = False,
    on_open_value: Optional[Callable[[bool], None]] = None,
    optional: bool = False,
    date_format: str = "%Y/%m/%d",
    first_day_of_the_week: int = 1,
    style: Optional[Union[str, Dict[str, str]]] = None,
    classes: Optional[List[str]] = None,
):
    """
    Show a textfield, which when clicked, opens a datepicker that allows users to select a range of dates by choosing a starting and ending date.
    The input dates should be stored in a reactive tuple of type `datetime.date`. The list should contain either precisely two elements.
    For an empty pre-selection of dates, pass a reactive empty list.

    ## Basic Example

    ```solara
    import solara
    import solara.lab as lab


    @solara.component
    def Page():
        dates = solara.use_reactive([])
        range_is_open = solara.use_reactive(False)

        with solara.Column():
            lab.InputDateRange(
                dates,
                open=range_is_open,
            )
    ```

    ## Arguments

    * value: Reactive tuple with elements of type `datetime.date`. For an empty pre-selection of dates, pass a reactive empty tuple.
    * label: Text used to label the text field that triggers the datepicker.
    * children: List of Elements to be rendered under the calendar. If empty, a close button is rendered.
    * open: Controls and communicates the state of the datepicker. If True, the datepicker is open. If False, the datepicker is closed.
    Intended to be used in conjunction with a custom set of controls to close the datepicker.
    * date_format: Sets the format of the date displayed in the text field. Defaults to `"%Y/%m/%d"`. For more information,
    see <a href="https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes" target="_blank">here</a>.
    * first_day_of_the_week: Sets the first day of the week, as an `int` starting count from Sunday (`=0`). Defaults to `1`, which is Monday.

    ## A More Advanced Example

    ```solara
    import solara
    import solara.lab as lab
    import datetime as dt


    @solara.component
    def Page():
        date = solara.use_reactive([])
        range_is_open = solara.use_reactive(False)
        stay_length = solara.use_reactive(1)

        controls = [
            solara.Button(
                label="Book",
                color="primary",
                on_click=lambda: range_is_open.set(not range_is_open.value),
            )
        ]

        def select_next_day(value):
            if len(value) != 0:
                value = value[0]
                second_date = value + dt.timedelta(days=stay_length.value)
                date.set([value, second_date])

        solara.use_memo(lambda: select_next_day(date.value), [stay_length.value])

        with solara.Column(style="width: 400px;"):
            solara.IntSlider("Length of stay", stay_length, min=1, max=10)
            with lab.InputDateRange(
                date,
                on_value=select_next_day,
                open=range_is_open,
            ):
                solara.Row(children=controls, justify="end", style="width: 100%;")
    ```
    """
    value_reactive = solara.use_reactive(value)
    del value
    date_standard_strings = [date.strftime("%Y-%m-%d") for date in value_reactive.value if date is not None]
    datepicker_is_open = solara.use_reactive(open_value, on_open_value)  # type: ignore
    del open_value, on_open_value
    style_flat = solara.util._flatten_style(style)

    def dates_to_string(dates: Tuple[Optional[dt.date], Optional[dt.date]]):
        string_dates = [date.strftime(date_format) if date is not None else "" for date in dates]
        if (len(dates) < 2 or dates[1] is None) and not optional:
            return string_dates[0], "Please select two dates"
        return " - ".join(string_dates), None

    def set_dates_cast(values):
        date_value = cast(
            Tuple[Optional[dt.date], Optional[dt.date]], tuple([dt.datetime.strptime(item, "%Y-%m-%d").date() if item is not None else None for item in values])
        )
        value_reactive.value = date_value
        if on_value:
            on_value(date_value)

    string_dates, error_message = dates_to_string(value_reactive.value)

    if error_message:
        label += f" ({error_message})"
    input = solara.v.TextField(
        label=label,
        v_model=string_dates,
        append_icon="mdi-calendar",
        error=bool(error_message),
        style_=style_flat,
        readonly=True,
        class_=", ".join(classes) if classes else "",
    )

    # We include closing on tab in case users want to skip the field with tab
    use_close_menu(input, datepicker_is_open)

    with solara.lab.Menu(
        activator=input,
        close_on_content_click=False,
        open_value=datepicker_is_open,
    ):
        with solara.v.DatePicker(
            v_model=date_standard_strings,
            on_v_model=set_dates_cast,
            range=True,
            first_day_of_week=first_day_of_the_week,
            style_="width: 100%;",
        ):
            if len(children) > 0:
                for el in children:
                    solara.display(el)
            else:
                with solara.Row(justify="end", style="width: 100%;"):
                    solara.Button("close", color="primary", on_click=lambda: datepicker_is_open.set(False))
