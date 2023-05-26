"""# Altair

[Altair](https://altair-viz.github.io/index.html) is a declarative statistical visualization library for Python.

This example show how to use the [on_click handler](/api/altair) to display data for a specific day in the chart.

Based on [an Altair example](https://altair-viz.github.io/gallery/annual_weather_heatmap.html)

"""
import altair as alt
import pandas as pd
from vega_datasets import data

import solara

# title = "Altair visualization"
source = data.seattle_weather()

selected_datum = solara.reactive(None)


@solara.component
def Page():
    def on_click(datum):
        selected_datum.value = datum

    chart = (
        alt.Chart(source, title="Daily Max Temperatures (C) in Seattle, WA")
        .mark_rect()
        .encode(
            alt.X("date(date):O").title("Day").axis(format="%e", labelAngle=0),
            alt.Y("month(date):O").title("Month"),
            alt.Color("max(temp_max)").title(None),
            tooltip=[
                alt.Tooltip("monthdate(date)", title="Date"),
                alt.Tooltip("max(temp_max)", title="Max Temp"),
            ],
        )
        .configure_view(step=13, strokeWidth=0)
        .configure_axis(domain=False)
    )
    with solara.Card("Annual Weather Heatmap for Seattle, WA"):
        solara.AltairChart(chart, on_click=on_click)
        df = source
        if selected_datum.value:
            month_date = selected_datum.value["monthdate_date_end"]
            dt = pd.to_datetime(month_date)
            df = df[(df["date"].dt.month == dt.month) & (df["date"].dt.day == dt.day)]
            solara.Markdown(f"Day of year: {dt.month_name()} - {dt.day}")
            solara.Button("Clear selection", on_click=lambda: selected_datum.set(None))
            solara.display(df)

            with solara.Details("Click data"):
                solara.Markdown(
                    f"""
                Click data:

                ```
                {selected_datum.value}
                ```
                """
                )
        else:
            solara.Markdown("Click on the chart to see data for a specific day")
