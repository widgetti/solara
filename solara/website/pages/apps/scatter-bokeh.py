import pathlib
import sys

from typing import Optional, cast

import vaex
import vaex.datasets

import solara
import solara.lab
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.transform import linear_cmap, factor_cmap

github_url = solara.util.github_url(__file__)
if sys.platform != "emscripten":
    pycafe_url = solara.util.pycafe_url(path=pathlib.Path(__file__),
                                        requirements=["vaex", "bokeh"])
else:
    pycafe_url = None

df_sample = vaex.datasets.titanic()


class State:
    color = solara.reactive(cast(Optional[str], None))
    x = solara.reactive(cast(Optional[str], None))
    y = solara.reactive(cast(Optional[str], None))
    df = solara.reactive(cast(Optional[vaex.DataFrame], None))

    @staticmethod
    def load_sample():
        State.x.value = "age"
        State.y.value = "fare"
        State.color.value = "body"
        State.df.value = df_sample

    @staticmethod
    def reset():
        State.df.value = None


@solara.component
def Page():
    df = State.df.value
    selected, on_selected = solara.use_state({"x": [0, 0]})  # noqa: SH101
    solara.provide_cross_filter()

    # the PivotTable will set this cross filter
    filter, _ = solara.use_cross_filter(id(df), name="scatter")

    # only apply the filter if the filter or dataframe changes
    def filter_df():
        if (filter is not None) and (df is not None):
            return df[filter]
        else:
            return df

    dff = solara.use_memo(filter_df, dependencies=[df, filter])

    with solara.AppBar():
        solara.lab.ThemeToggle()
    with solara.Sidebar():
        with solara.Card("Controls", margin=0, elevation=0):
            with solara.Column():
                with solara.Row():
                    solara.Button("Sample dataset",
                                  color="primary",
                                  text=True,
                                  outlined=True,
                                  on_click=State.load_sample,
                                  disabled=df is not None)
                    solara.Button("Clear dataset",
                                  color="primary",
                                  text=True,
                                  outlined=True,
                                  on_click=State.reset)

                if df is not None:
                    columns = df.get_column_names()
                    solara.Select("Column x", values=columns, value=State.x)
                    solara.Select("Column y", values=columns, value=State.y)
                    solara.Select("Color", values=columns, value=State.color)

                    solara.PivotTable(df, ["pclass"], ["sex"],
                                      selected=selected,
                                      on_selected=on_selected)

    if dff is not None:
        source = ColumnDataSource(
            data={
                "x": dff[State.x.value].values,
                "y": dff[State.y.value].values,
                "z": dff[State.color.value].values,
            })
        if State.x.value and State.y.value:
            p = figure(x_axis_label=State.x.value,
                       y_axis_label=State.y.value,
                       width_policy="max",
                       height=700)

            # add a scatter, colorbar, and mapper
            color_expr = dff[State.color.value]
            if (color_expr.dtype == "string") or (color_expr.dtype == "bool"):
                mapper = factor_cmap
                factors = color_expr.unique()
                try:
                    factors.remove(None)
                except ValueError:
                    pass
                args = dict(
                    palette=f"Viridis{min(11, max(3, color_expr.nunique()))}",
                    factors=factors)
            else:
                mapper = linear_cmap
                args = dict(palette="Viridis256",
                            low=color_expr.min()[()],
                            high=color_expr.max()[()])

            s = p.scatter(source=source,
                          x="x",
                          y="y",
                          size=12,
                          fill_color=mapper(field_name="z", **args))
            p.add_layout(
                s.construct_color_bar(title=State.color.value,
                                      label_standoff=6,
                                      padding=5,
                                      border_line_color=None), "right")

            solara.lab.FigureBokeh(p, dark_theme="carbon")

        else:
            solara.Warning("Select x and y columns")

    else:
        solara.Info(
            "No data loaded, click on the sample dataset button to load a sample dataset, or upload a file."
        )

    with solara.Column(style={"max-width": "400px"}):
        solara.Button(label="View source",
                      icon_name="mdi-github-circle",
                      attributes={
                          "href": github_url,
                          "target": "_blank"
                      },
                      text=True,
                      outlined=True)
        if sys.platform != "emscripten":
            solara.Button(
                label="Edit this example live on py.cafe",
                icon_name="mdi-coffee-to-go-outline",
                attributes={
                    "href": pycafe_url,
                    "target": "_blank"
                },
                text=True,
                outlined=True,
            )


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    dark_effective = solara.lab.use_dark_effective()
    return solara.AppLayout(children=children,
                            toolbar_dark=dark_effective,
                            color=None)  # if dark_effective else "primary")
