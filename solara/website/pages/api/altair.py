"""# FigureAltair

"""

import altair as alt
import pandas as pd

import solara
from solara.website.utils import apidoc

title = "FigureAltair"

df = pd.DataFrame({"a": ["A", "B", "C", "D", "E", "F", "G", "H", "I"], "b": [28, 55, 43, 91, 81, 53, 19, 87, 52]})


@solara.component
def Page():
    click_data, set_click_data = solara.use_state(None)
    hover_data, set_hover_data = solara.use_state(None)

    chart = alt.Chart(df).mark_bar().encode(x="a", y="b")

    with solara.Div() as main:
        solara.AltairChart(chart, on_click=set_click_data, on_hover=set_hover_data)

        solara.Markdown(
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


__doc__ += apidoc(solara.FigureAltair.f)  # type: ignore
