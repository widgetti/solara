"""This Page components sets in the package root and takes two non-optional arguments,
meaning it will catch urls like /viz/scatter/titanic and pass two argument to the Page component,
so we can render content dynamically.

The extra x and y must be optional arguments, and can be changed using the query parameters, e.g.:
/viz/tabular/titanic?x=1&page_size=50
"""
import plotly.express as px
import solara

from ... import data
from ...components import Layout


def title(type: str, name: str):
    return f"Solara viz view: {type} - {name}"


@solara.component
def Page(type: str, name: str, x: str = None, y: str = None):
    # router = solara.use_router()
    df = data.dfs[name].df
    with Layout() as main:
        fig = None
        if type == "scatter":
            column_names = df.get_column_names()
            x = solara.ui_dropdown("x", column_names[0], column_names)
            y = solara.ui_dropdown("y", column_names[1], column_names)
            if x and y:
                fig = px.scatter(df.to_pandas_df(), x=x, y=y)
            else:
                solara.Warning("Please provide x and y")
        elif type == "histogram":
            x = solara.ui_dropdown("x")
            if x:
                fig = px.histogram(df, x=x)
            else:
                solara.Warning("Please provide x")
        else:
            solara.Error("Uknonwn ")
        if fig:
            solara.FigurePlotly(fig, dependencies=[x, y])
        # router.set_query(x=x, y=y)
    return main
