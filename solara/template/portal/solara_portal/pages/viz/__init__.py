"""This Page components sets in the package root and takes two non-optional arguments,
meaning it will catch urls like /viz/scatter/titanic and pass two argument to the Page component,
so we can render content dynamically.
"""
from typing import Optional

import plotly.express as px
import solara

from ... import data


def title(type: str, name: str):
    return f"Solara viz view: {type} - {name}"


@solara.component
def Page(type: Optional[str] = None, name: Optional[str] = None, x: Optional[str] = None, y: Optional[str] = None):
    type, set_type = solara.use_state_or_update(type)
    name, set_name = solara.use_state_or_update(name)
    x, set_x = solara.use_state_or_update(x)
    y, set_y = solara.use_state_or_update(y)

    with solara.ColumnsResponsive(12) as main:
        if type is None:
            type = "scatter"
            set_type("scatter")
        with solara.Sidebar():
            with solara.Card("Viz configuration"):
                solara.Select(label="dataset", value=name, values=list(data.dfs), on_value=set_name)
                solara.ToggleButtonsSingle(value=type, values=["scatter", "histogram"], on_value=set_type)
        if name not in data.dfs:
            set_name(list(data.dfs)[0])
        if name in data.dfs:
            df = data.dfs[name].df
            column_names = df.get_column_names()
            df = df.to_pandas_df()
            if x not in column_names:
                set_x(column_names[0])
            if y not in column_names:
                set_y(column_names[1])
            if x not in column_names:
                set_x(column_names[0])
            if y not in column_names:
                set_y(column_names[1])
            solara.Title(f"Solara demo » viz » {type} » {name}")
            fig = None
            if type == "scatter":
                with solara.Sidebar():
                    with solara.Card("Columns"):
                        solara.Select(label="x", value=x, values=column_names, on_value=set_x)
                        solara.Select(label="y", value=y, values=column_names, on_value=set_y)
                if x and y and x in column_names and y in column_names:
                    fig = px.scatter(df, x=x, y=y)
                else:
                    solara.Warning("Please provide x and y")
            elif type == "histogram":
                with solara.Sidebar():
                    with solara.Card("Columns"):
                        solara.Select(label="x", value=x, values=column_names, on_value=set_x)
                if x and x in column_names:
                    fig = px.histogram(df, x=x)
                else:
                    solara.Warning("Please provide x")
            else:
                solara.Error("Uknonwn ")
            if fig:
                solara.FigurePlotly(fig, dependencies=[name, type, x, y])
    return main
