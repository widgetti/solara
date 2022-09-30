import pandas as pd
import plotly.express as px
import solara

try:
    df = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv")
except Exception:
    df = None

if df is not None:
    year_min = df["year"].min()
    year_max = df["year"].max()
    years = df["year"].unique().tolist()


@solara.component
def Page():
    with solara.Div() as main:
        solara.Markdown(
            """# Plotly
Solara supports plotly and plotly express. Create your figure (not a figure widget)
and pass it to the FigurePlotly component.
"""
        )
        index = solara.ui_slider(value=0, min=0, max=len(years) - 1, tick_labels=years, key="year slider index")
        selected_year = years[index]

        filtered_df = df[df.year == selected_year].copy()

        fig = px.scatter(filtered_df, x="gdpPercap", y="lifeExp", size="pop", color="continent", hover_name="country", log_x=True, size_max=55)
        fig.update_layout(transition_duration=1500)

        solara.FigurePlotly(fig, dependencies=[selected_year])
    return main
