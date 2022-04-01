import altair as alt
import pandas as pd
from vega_datasets import data

from solara.kitchensink import react, sol


@react.component
def Altair():
    click_data, set_click_data = react.use_state(None)
    hover_data, set_hover_data = react.use_state(None)

    if 0:
        # to bad this example doesn't work well with on_click and on_hover
        source = data.cars()
        chart = (
            alt.Chart(source)
            .mark_circle(size=60)
            .encode(x="Horsepower", y="Miles_per_Gallon", color="Origin", tooltip=["Name", "Origin", "Horsepower", "Miles_per_Gallon"])
            .interactive()
        )
    else:
        source = pd.DataFrame({"a": ["A", "B", "C", "D", "E", "F", "G", "H", "I"], "b": [28, 55, 43, 91, 81, 53, 19, 87, 52]})

        chart = alt.Chart(source).mark_bar().encode(x="a", y="b")

    with sol.Div() as main:
        sol.MarkdownIt(
            """
Altair is supported since we can render vega lite.
We also support on_click and on_hover events.
```python
source = pd.DataFrame({{
    "a": ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
    "b": [28, 55, 43, 91, 81, 53, 19, 87, 52]
}})
chart = alt.Chart(source).mark_bar().encode(x="a", y="b")
sol.AltairChart(chart, on_click=set_click_data, on_hover=set_hover_data)
```
            """
        )
        sol.AltairChart(chart, on_click=set_click_data, on_hover=set_hover_data)

        sol.Markdown(
            f"""
Click data:

```
{click_data}
```

Hover data:
```
{hover_data}
```
            """
        )

    return main


app = Altair()
