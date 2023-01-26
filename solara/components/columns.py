import itertools
from typing import List, Union

import reacton.ipyvuetify as rv

import solara


def cycle(value):
    if value is None:
        return itertools.cycle([None])
    elif isinstance(value, int):
        return itertools.cycle([value])
    elif isinstance(value, (list, tuple)):
        return itertools.cycle(value)
    else:
        raise ValueError(f"Invalid value for columns: {value}, should be None, int, or list/tuple.")


@solara.component
def Columns(
    widths: List[Union[float, int]] = [1],
    wrap=True,
    gutters=True,
    gutters_dense=False,
    children=[],
):
    """Lays out children in columns, with relative widths specified as a list of floats or ints.

    Widths are relative to each other, so [1, 2, 1] will result in 1/4, 1/2, 1/4 width columns.

    If there are more children than widths, the width list will be cycled.

    ```python
    with solara.Columns([1, 2, 1]):
        with solara.Column():
            solara.Text("I am on the left")
        with solara.Card("Middle"):
            ...
        with solara.Column():
            ...

    ```

    When three children are added to this component, they will be laid out in three columns,
    with the first and last column taking up 1/4 of the width, and the middle column taking up 1/2 of the width.

    # Arguments

     * widths: List of floats or ints, specifying the relative widths of the columns.
     * wrap: Whether to wrap the columns to the next row if there is not enough space available.
     * gutters: Whether to add gutters between the columns.
     * gutters_dense: Make gutters smaller.
     * children: List of children to be laid out in columns.

    """
    with rv.Container() as main:
        with rv.Row(class_="flex-nowrap" if not wrap else "", no_gutters=not gutters, dense=gutters_dense):
            for child, width in zip(children, cycle(widths)):
                with rv.Col(children=[child], style_=f"flex-grow: {width};"):
                    pass
    return main


@solara.component
def ColumnsResponsive(default=None, small=None, medium=None, large=None, xlarge=None, children=[], wrap=True, gutters=True, gutters_dense=False):
    """Lay our children in columns, on a 12 point grid system that is responsive to screen size.

    If a single number is specified, or less values than children, the values will be cycled.
    The total width of this system is 12, so if you want to have 3 columns, each taking up 4 points, you would specify [4, 4, 4] or 4.


    ```python
    with ColumnsResponsive([4, 4, 4]):
        ...
    with ColumnsResponsive(4):  # same effect
        ...
    ```

    If you want the first column to take up 4 points, and the second column to take up the remaining 8 points, you would specify [4, 8].

    ```python
    with ColumnsResponsive([4, 8]):
        ...
    ```

    If you want your columns to be full width on large screen, and next to eachother on larger screens.

    ```python
    with ColumnsResponsive(12, large=[4, 8]):
        ...
    ```

    # Arguments

     * default: Width of column for >= 0 px.
     * small: Width of column for >= 600 px.
     * medium: Width of column >= 960 px.
     * large: Width of column for >= 1264 px.
     * xlarge: Width of column for >= 1904 px.

    """

    def cycle(value):
        if value is None:
            return itertools.cycle([None])
        elif isinstance(value, int):
            return itertools.cycle([value])
        elif isinstance(value, (list, tuple)):
            return itertools.cycle(value)
        else:
            raise ValueError(f"Invalid value for columns: {value}, should be None, int, or list/tuple.")

    with rv.Container() as main:
        with rv.Row(class_="flex-nowrap" if not wrap else "", no_gutters=not gutters, dense=gutters_dense):
            for child, xsmall, small, medium, large, xlarge in zip(children, cycle(default), cycle(small), cycle(medium), cycle(large), cycle(xlarge)):
                with rv.Col(
                    cols=xsmall,
                    sm=small,
                    md=medium,
                    lg=large,
                    xl=xlarge,
                    children=[child],
                ):
                    pass
    return main
