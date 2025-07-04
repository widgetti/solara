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
    date_picker_type: str = "date",
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    dense: bool = False,
    hide_details: Union[str, bool] = "auto",
    placeholder: Optional[str] = None,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
    clearable: bool = False,
):
    """
    Show a textfield, which when clicked, opens a datepicker. The input date should be of type `datetime.date`.

    ## Basic Example

    ```solara
    import solara
    import solara.lab
    import datetime as dt


    @solara.component
    def Page():
        date = solara.use_reactive(dt.date.today())

        solara.lab.InputDate(date)
        solara.Text(str(date.value))
    ```

    ## Arguments

    * value: Reactive variable of type `datetime.date`, or `None`. This date is selected the first time the component is rendered.
    * on_value: a callback function for when value changes. The callback function receives the new value as an argument.
    * label: Text used to label the text field that triggers the datepicker.
    * children: List of Elements to be rendered under the calendar. If empty, a close button is rendered.
    * open_value: Controls and communicates the state of the datepicker. If True, the datepicker is open. If False, the datepicker is closed.
    Intended to be used in conjunction with a custom set of controls to close the datepicker.
    * on_open_value: a callback function for when open_value changes. Also receives the new value as an argument.
    * optional: Determines whether to show an error when value is `None`. If `True`, no error is shown.
    * date_format: Sets the format of the date displayed in the text field. Defaults to `"%Y/%m/%d"`. For more information, see
    <a href="https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes" target="_blank">the Python documentation</a>.
    * first_day_of_the_week: Sets the first day of the week, as an `int` starting count from Sunday (`=0`). Defaults to `1`, which is Monday.
    * style: CSS style to apply to the text field. Either a string or a dictionary of CSS properties (i.e. `{"property": "value"}`).
    * classes: List of CSS classes to apply to the text field.
    * date_picker_type: Sets the type of the datepicker. Use `"date"` for date selection or `"month"` for month selection. Defaults to `"date"`.
    * min_date: Earliest allowed date/month (ISO 8601 format). If not specified, there is no limit.
    * max_date: Latest allowed date/month (ISO 8601 format). If not specified, there is no limit.
    * dense: Reduces the input height.
    * hide_details: Hides hint and validation errors. When set to 'auto', messages will be rendered only if there's a message (hint, error message, counter value etc) to display.
    * placeholder: Sets the input's placeholder text.
    * prefix: Displays prefix text.
    * suffix: Displays suffix text.
    * clearable: Whether the input can be cleared.
    """
    value_reactive = solara.use_reactive(value, on_value)  # type: ignore
    del value, on_value
    datepicker_is_open = solara.use_reactive(open_value, on_open_value)  # type: ignore
    del open_value, on_open_value

    if date_picker_type == "date":
        internal_date_format = "%Y-%m-%d"
    elif date_picker_type == "month":
        internal_date_format = "%Y-%m"
    else:
        raise ValueError("date_picker_type must be either 'date' or 'month'.")

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
            date_value = dt.datetime.strptime(new_value, internal_date_format).date()
            datepicker_is_open.set(False)
            value_reactive.value = date_value

    def standard_strfy(date: Optional[dt.date]):
        if date is None:
            return None
        else:
            return date.strftime(internal_date_format)

    date_standard_str = standard_strfy(value_reactive.value)

    style_flat = solara.util._flatten_style(style)

    internal_value, error_message, set_value_cast = _use_input_type(value_reactive, set_date_typed_cast, date_to_str)

    if error_message:
        label += f" ({error_message})"
    input = solara.v.TextField(
        label=label,
        v_model=internal_value,
        on_v_model=set_value_cast,
        append_icon="mdi-calendar",
        error=bool(error_message),
        style_="min-width: 290px;" + style_flat,
        class_=", ".join(classes) if classes else "",
        dense=dense,
        hide_details=hide_details,
        placeholder=placeholder if placeholder is not None else "",
        prefix=prefix if prefix is not None else "",
        suffix=suffix if suffix is not None else "",
        clearable=clearable,
    )

    use_close_menu(input, datepicker_is_open)

    with solara.lab.Menu(
        activator=input,
        close_on_content_click=False,
        open_value=datepicker_is_open,
        use_activator_width=False,
    ):
        with solara.v.DatePicker(
            v_model=date_standard_str,
            on_v_model=set_date_cast,
            first_day_of_week=first_day_of_the_week,
            style_="width: 100%;",
            max=max_date,  # type: ignore
            min=min_date,  # type: ignore
            type=date_picker_type,
        ):
            if len(children) > 0:
                solara.display(*children)


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
    date_picker_type: str = "date",
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    sort: Optional[bool] = False,
    dense: bool = False,
    hide_details: Union[str, bool] = "auto",
    placeholder: Optional[str] = None,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
):
    """
    Show a textfield, which when clicked, opens a datepicker that allows users to select a range of dates by choosing a starting and ending date.
    The input dates should be stored in a reactive tuple of type `datetime.date`. The list should contain either precisely two elements.
    For an empty pre-selection of dates, pass a reactive empty list.

    ## Basic Example

    ```solara
    import solara
    import solara.lab
    import datetime as dt


    @solara.component
    def Page():
        dates = solara.use_reactive(tuple([dt.date.today(), dt.date.today() + dt.timedelta(days=1)]))

        solara.lab.InputDateRange(dates)
        solara.Text(str(dates.value))
    ```

    ## Arguments

    * value: Tuple with elements of type `datetime.date`. For an empty pre-selection of dates, pass an empty tuple.
    * on_value: a callback function for when value changes. The callback function receives the new value as an argument.
    * label: Text used to label the text field that triggers the datepicker.
    * children: List of Elements to be rendered under the calendar. If empty, a close button is rendered.
    * open_value: Controls and communicates the state of the datepicker. If True, the datepicker is open. If False, the datepicker is closed.
    Intended to be used in conjunction with a custom set of controls to close the datepicker.
    * on_open_value: a callback function for when open_value changes. Also receives the new value as an argument.
    * date_format: Sets the format of the date displayed in the text field. Defaults to `"%Y/%m/%d"`. For more information,
    see <a href="https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes" target="_blank">the Python documentation</a>.
    * optional: Determines whether go show an error when value is `None`. If `True`, no error is shown.
    * first_day_of_the_week: Sets the first day of the week, as an `int` starting count from Sunday (`=0`). Defaults to `1`, which is Monday.
    * style: CSS style to apply to the text field. Either a string or a dictionary of CSS properties (i.e. `{"property": "value"}`).
    * classes: List of CSS classes to apply to the text field.
    * date_picker_type: Sets the type of the datepicker. Use `"date"` for date selection or `"month"` for month selection. Defaults to `"date"`.
    * min_date: Earliest allowed date/month (ISO 8601 format). If not specified, there is no limit.
    * max_date: Latest allowed date/month (ISO 8601 format). If not specified, there is no limit.
    * sort: If True, selected dates will be sorted in ascending order, regardless of the order they were picked. If False, preserves the order the
    dates were selected.
    * dense: Reduces the input height.
    * hide_details: Hides hint and validation errors. When set to 'auto', messages will be rendered only if there's a message (hint, error message, counter value etc) to display.
    * placeholder: Sets the input's placeholder text.
    * prefix: Displays prefix text.
    * suffix: Displays suffix text.

    ## A More Advanced Example

    ```solara
    import solara
    import solara.lab
    import datetime as dt


    @solara.component
    def Page():
        date = solara.use_reactive(tuple([dt.date.today(), None]))
        range_is_open = solara.use_reactive(False)
        stay_length = solara.use_reactive(1)

        def set_end_date(value):
            if value and value[0]:
                value = value[0]
                second_date = value + dt.timedelta(days=stay_length.value)
                date.set([value, second_date])

        def book():
            # Do some stuff here
            range_is_open.set(False)

        solara.use_memo(lambda: set_end_date(date.value), [stay_length.value])

        with solara.Column(style="width: 400px;"):
            solara.IntSlider("Length of stay", stay_length, min=1, max=10)
            with solara.lab.InputDateRange(
                date,
                on_value=set_end_date,
                open_value=range_is_open,
            ):
                with solara.Row(justify="end", style="width: 100%;"):
                    solara.Button(
                        label="Book",
                        color="primary",
                        on_click=book,
                    )

    ```
    """
    value_reactive = solara.use_reactive(value, on_value)  # type: ignore
    del value, on_value

    if date_picker_type == "date":
        internal_date_format = "%Y-%m-%d"
    elif date_picker_type == "month":
        internal_date_format = "%Y-%m"
    else:
        raise ValueError("date_picker_type must be either 'date' or 'month'.")

    date_standard_strings = [date.strftime(internal_date_format) for date in value_reactive.value if date is not None]
    datepicker_is_open = solara.use_reactive(open_value, on_open_value)  # type: ignore
    del open_value, on_open_value
    style_flat = solara.util._flatten_style(style)

    def dates_to_string(dates: Tuple[Optional[dt.date], Optional[dt.date]]):
        string_dates = [date.strftime(date_format) if date is not None else "" for date in dates]
        if (len(dates) < 2 or dates[1] is None) and not optional:
            return string_dates[0], f"Please select two {date_picker_type}s"
        return " - ".join(string_dates), None

    def set_dates_cast(values):
        date_value = cast(
            Tuple[Optional[dt.date], Optional[dt.date]],
            tuple([(dt.datetime.strptime(item, internal_date_format).date() if item is not None else None) for item in values]),
        )
        if len(date_value) > 1 and date_value[1] is not None:
            datepicker_is_open.set(False)

            if sort:
                date_value = cast(Tuple[dt.date, dt.date], tuple(sorted(date_value)))

        value_reactive.value = date_value

    string_dates, error_message = dates_to_string(value_reactive.value)

    if error_message:
        label += f" ({error_message})"
    input = solara.v.TextField(
        label=label,
        v_model=string_dates,
        append_icon="mdi-calendar",
        error=bool(error_message),
        style_="min-width: 290px;" + style_flat,
        readonly=True,
        class_=", ".join(classes) if classes else "",
        dense=dense,
        hide_details=hide_details,
        placeholder=placeholder if placeholder is not None else "",
        prefix=prefix if prefix is not None else "",
        suffix=suffix if suffix is not None else "",
    )

    # We include closing on tab in case users want to skip the field with tab
    use_close_menu(input, datepicker_is_open)

    with solara.lab.Menu(
        activator=input,
        close_on_content_click=False,
        open_value=datepicker_is_open,
        use_activator_width=False,
    ):
        with solara.v.DatePicker(
            v_model=date_standard_strings,
            on_v_model=set_dates_cast,
            range=True,
            first_day_of_week=first_day_of_the_week,
            style_="width: 100%;",
            max=max_date,  # type: ignore
            min=min_date,  # type: ignore
            type=date_picker_type,
        ):
            if len(children) > 0:
                for el in children:
                    solara.display(el)
