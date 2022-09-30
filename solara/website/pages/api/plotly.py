"""Renders a plotly figure object and support for events.

You can use a regular plotly figure, for instance using plotly.express.

Supported events are include in the example below.

For performance, a dependency list can be provided. Any change to the dependency list will cause the Figure data to be updated.
This can be significantly faster than comparing he figure data directly.

"""

import plotly.express as px
import solara

df = px.data.iris()


@solara.component
def Page():
    with solara.VBox() as main:
        selection_data, set_selection_data = solara.use_state(None)
        click_data, set_click_data = solara.use_state(None)
        hover_data, set_hover_data = solara.use_state(None)
        unhover_data, set_unhover_data = solara.use_state(None)
        deselect_data, set_deselect_data = solara.use_state(None)
        fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species")
        solara.FigurePlotly(
            fig, on_selection=set_selection_data, on_click=set_click_data, on_hover=set_hover_data, on_unhover=set_unhover_data, on_deselect=set_deselect_data
        )

        solara.Markdown(
            f"""
# Events data
## selection
```
{selection_data}
```

## click
```
{click_data}
```

## hover
```
{hover_data}
```

## unhover
```
{unhover_data}
```

## deselect
```
{deselect_data}
```


"""
        )
    return main
