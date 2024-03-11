from typing import Optional, cast

import pandas as pd

import solara
import solara.express as solara_px  # similar to plotly express, but comes with cross filters
import solara.lab
from solara.components.columns import Columns
from solara.components.file_drop import FileDrop

github_url = solara.util.github_url(__file__)
try:
    # fails on pyodide
    df_sample = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv")
except:  # noqa
    df_sample = None


class State:
    size_max = solara.reactive(40.0)
    size = solara.reactive(cast(Optional[str], None))
    color = solara.reactive(cast(Optional[str], None))
    x = solara.reactive(cast(Optional[str], None))
    y = solara.reactive(cast(Optional[str], None))
    logx = solara.reactive(False)
    logy = solara.reactive(False)
    df = solara.reactive(cast(Optional[pd.DataFrame], None))

    @staticmethod
    def load_sample():
        State.x.value = "gdpPercap"
        State.y.value = "lifeExp"
        State.size.value = "pop"
        State.color.value = "continent"
        State.logx.value = True
        State.df.value = df_sample

    @staticmethod
    def load_from_file(file):
        df = pd.read_csv(file["file_obj"])
        State.x.value = str(df.columns[0])
        State.y.value = str(df.columns[1])
        State.size.value = str(df.columns[2])
        State.color.value = str(df.columns[3])
        State.df.value = df

    @staticmethod
    def reset():
        State.df.value = None


@solara.component
def Page():
    df = State.df.value
    dark_effective = solara.lab.use_dark_effective()

    # the .scatter will set this cross filter
    filter, _set_filter = solara.use_cross_filter(id(df))

    # only apply the filter if the filter or dataframe changes
    def filter_df():
        if filter is not None and df is not None:
            return df.loc[filter]

    dff = solara.use_memo(filter_df, dependencies=[df, filter])

    with solara.AppBar():
        solara.lab.ThemeToggle()
    with solara.Sidebar():
        with solara.Card("Controls", margin=0, elevation=0):
            with solara.Column():
                with solara.Row():
                    solara.Button("Sample dataset", color="primary", text=True, outlined=True, on_click=State.load_sample, disabled=df is not None)
                    solara.Button("Clear dataset", color="primary", text=True, outlined=True, on_click=State.reset)
                FileDrop(on_file=State.load_from_file, on_total_progress=lambda *args: None, label="Drag file here")

                if df is not None:
                    solara.SliderFloat(label="Size", value=State.size_max, min=1, max=100)
                    solara.Checkbox(label="Log x", value=State.logx)
                    solara.Checkbox(label="Log y", value=State.logy)
                    columns = list(map(str, df.columns))
                    solara.Select("Column x", values=columns, value=State.x)
                    solara.Select("Column y", values=columns, value=State.y)
                    solara.Select("Size", values=columns, value=State.size)
                    solara.Select("Color", values=columns, value=State.color)
                    if filter is None:
                        solara.Info("If you select points in the scatter plot, you can download the points here.")
                    else:

                        def get_data():
                            return dff.to_csv(index=False)

                        solara.FileDownload(get_data, label=f"Download {len(dff):,} selected points", filename="selected.csv")

    if df is not None:
        with Columns(widths=[2, 4]):
            if State.x.value and State.y.value:
                solara_px.scatter(
                    df,
                    State.x.value,
                    State.y.value,
                    size=State.size.value,
                    color=State.color.value,
                    size_max=State.size_max.value,
                    log_x=State.logx.value,
                    log_y=State.logy.value,
                    template="plotly_dark" if dark_effective else "plotly_white",
                )
            else:
                solara.Warning("Select x and y columns")

    else:
        solara.Info("No data loaded, click on the sample dataset button to load a sample dataset, or upload a file.")

    solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    dark_effective = solara.lab.use_dark_effective()
    return solara.AppLayout(children=children, toolbar_dark=dark_effective, color=None)  # if dark_effective else "primary")
