import pandas as pd
import plotly.express as px

from solara.kitchensink import react, sol

df = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv")

year_min = df["year"].min().item()
year_max = df["year"].max().item()
years = df["year"].unique().tolist()


@react.component
def Plotly():
    with sol.Div() as main:
        sol.Markdown(
            """# Plotly
Solara supports plotly and plotly express. Create your figure (not a figure widget)
and pass it to the FigurePlotly component.
"""
        )
        index = sol.ui_slider(value=0, min=0, max=len(years) - 1, tick_labels=years, key="year slider index")
        selected_year = years[index]

        filtered_df = df[df.year == selected_year].copy()

        fig = px.scatter(filtered_df, x="gdpPercap", y="lifeExp", size="pop", color="continent", hover_name="country", log_x=True, size_max=55)
        fig.update_layout(transition_duration=1500)

        sol.FigurePlotly(fig, dependencies=[selected_year])
    return main


app = Plotly()
