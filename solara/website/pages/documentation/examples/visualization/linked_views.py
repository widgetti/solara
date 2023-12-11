"""# Linked views

This example shows how to create linked views. The clicked row information is passed up to the parent component using an event,
and then passed down to both child components.

"""

import dataclasses
from typing import Callable, cast

import plotly.express as px

import solara

df = px.data.iris()
columns = list(df.columns)


@dataclasses.dataclass
class ClickPoint:
    row_index: int
    x_column: str
    y_column: str


def find_row_index(fig, click_data):
    # goes from trace index and point index to row index in a dataframe
    # requires passing df.index as to custom_data
    trace_index = click_data["points"]["trace_indexes"][0]
    point_index = click_data["points"]["point_indexes"][0]
    trace = fig.data[trace_index]
    return trace.customdata[point_index][0]


@solara.component
def ClickScatter(df, x, y, color, click_row, on_click: Callable[[ClickPoint], None]):
    x, set_x = solara.use_state(x)
    y, set_y = solara.use_state(y)
    fig = px.scatter(df, x, y, color=color, custom_data=[df.index])

    def on_click_trace(click_data):
        # sanity checks
        assert click_data["event_type"] == "plotly_click"
        row_index = find_row_index(fig, click_data)
        on_click(ClickPoint(row_index, x, y))

    if click_row:
        click_x = df[x].values[click_row]
        click_y = df[y].values[click_row]
        fig.add_trace(px.scatter(x=[click_x], y=[click_y], text=["⭐️"]).data[0])
    # make the figure a bit smaller
    fig.update_layout(width=400)
    with solara.VBox() as main:
        solara.FigurePlotly(fig, on_click=on_click_trace)
        solara.Select(label="X-axis", value=x, values=columns, on_value=set_x)
        solara.Select(label="Y-axis", value=y, values=columns, on_value=set_y)
    return main


@solara.component
def Page():
    click_point, set_click_point = solara.use_state(cast(ClickPoint, None))
    if click_point:
        clicked_row = click_point.row_index
    else:
        clicked_row = None

    with solara.VBox() as main:
        with solara.HBox():
            ClickScatter(df, "sepal_length", "sepal_width", "species", clicked_row, on_click=set_click_point)
            ClickScatter(df, "petal_length", "petal_width", "species", clicked_row, on_click=set_click_point)
        if click_point is not None:
            clicked_row = click_point.row_index
            solara.Success(f"Clicked on row {clicked_row}. Which is highlighted in the both plots.")
            solara.Markdown(
                f"""
            ```python
            row_data = {df.iloc[clicked_row].to_dict()}
            ```"""
            )
        else:
            solara.Info("Click to select a point")

    return main
