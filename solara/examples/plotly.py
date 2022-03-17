from solara.kitchensink import *
import plotly.express as px

import pandas as pd

df = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv")

year_min = df["year"].min().item()
year_max = df["year"].max().item()
years = df["year"].unique().tolist()

import solara.widgets

solara.widgets.watch()


@react.component
def Plotly():
    with Div() as main:
        Markdown(
            """# Plotly
Solara supports plotly and plotly express. Create your figure (not a figure widget)
and pass it to the FigurePlotly component.
"""
        )
        index = ui_slider(value=0, min=0, max=len(years) - 1, tick_labels=years, key="year slider index")
        print(years)
        selected_year = years[index]

        filtered_df = df[df.year == selected_year].copy()

        fig = px.scatter(filtered_df, x="gdpPercap", y="lifeExp", size="pop", color="continent", hover_name="country", log_x=True, size_max=55)
        fig.update_layout(transition_duration=1500)

        # def on_click(*args, **kwargs):
        #     print(args, kwargs)

        # import plotly.graph_objs as go
        # from ipywidgets import Output, VBox

        # fig = go.Figure()
        # pie = fig.add_pie(values=[1, 2, 3])

        # # def handle_click(trace, points, state, *args):
        def handle_click(*args):
            print("handle click", args)

        FigurePlotly(fig, on_click=handle_click)  # , on_hover=handle_click)
    return main
