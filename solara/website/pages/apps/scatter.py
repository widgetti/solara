from typing import Optional, cast

import pandas as pd
import plotly.express as px

import solara
import solara.lab
from solara.components.columns import Columns
from solara.components.file_drop import FileDrop

size_max = solara.lab.Reactive[float](40)
size = solara.lab.Reactive[Optional[str]](None)
color = solara.lab.Reactive[Optional[str]](None)
x = solara.lab.Reactive[Optional[str]](None)
y = solara.lab.Reactive[Optional[str]](None)
logx = solara.lab.Reactive[bool](False)
logy = solara.lab.Reactive[bool](False)


df_sample = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv")
github_url = solara.util.github_url(__file__)


@solara.component
def Page():
    size.use()
    color.use()
    size_max.use()
    x.use()
    y.use()
    logx.use()
    logy.use()
    df, set_df = solara.use_state(cast(Optional[pd.DataFrame], None), eq=lambda *args: False)

    def load_sample():
        x.value = str("gdpPercap")
        y.value = str("lifeExp")
        size.value = str("pop")
        color.value = str("continent")
        logx.value = True
        set_df(df_sample)

    def load_from_file(file):
        df = pd.read_csv(file["file_obj"])
        x.value = str(df.columns[0])
        y.value = str(df.columns[1])
        size.value = str(df.columns[2])
        color.value = str(df.columns[3])
        set_df(df)

    with solara.Sidebar():
        with solara.Card("Controls", margin=0, elevation=0):
            with solara.Column():
                with solara.Row():
                    solara.Button("Sample dataset", color="primary", text=True, outlined=True, on_click=load_sample)
                    solara.Button("Clear dataset", color="primary", text=True, outlined=True, on_click=lambda: set_df(None))
                FileDrop(on_file=load_from_file, on_total_progress=lambda *args: None, label="Drag file here")

                if df is not None:
                    solara.FloatSlider("Size", max=60).connect(size_max)
                    solara.Checkbox(label="Log x").connect(logx)
                    solara.Checkbox(label="Log y").connect(logy)
                    columns = list(map(str, df.columns))
                    solara.Select("Column x", values=columns).connect(x)  # type: ignore
                    solara.Select("Column y", values=columns).connect(y)  # type: ignore
                    solara.Select("Size", values=columns).connect(size)  # type: ignore
                    solara.Select("Color", values=columns).connect(color)  # type: ignore

    if df is not None:
        with Columns(widths=[2, 4]):
            if x.value and y.value:
                fig = px.scatter(df, x.value, y.value, size=size.value, color=color.value, size_max=size_max.value, log_x=logx.value, log_y=logy.value)
                solara.FigurePlotly(fig)
            else:
                solara.Warning("Select x and y columns")

    else:
        solara.Info("No data loaded, click on the sample dataset button to load a sample dataset, or upload a file.")

    solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    return solara.AppLayout(children=children)
