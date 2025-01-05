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
    state = solara.use_reactive(
        {
            "selection_data": None,
            "click_data": None,
            "hover_data": None,
            "unhover_data": None,
            "deselect_data": None,
        }
    )

    fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species")
    solara.FigurePlotly(
        fig, 
        on_selection=lambda data: state.set({**state.value, "selection_data": data}),
        on_click=lambda data: state.set({**state.value, "click_data": data}),
        on_hover=lambda data: state.set({**state.value, "hover_data": data}),
        on_unhover=lambda data: state.set({**state.value, "unhover_data": data}),
        on_deselect=lambda data: state.set({**state.value, "deselect_data": data}),
    )

    solara.Markdown(
        f"""
# Events data
## selection
```
{state.value['selection_data']}
```

## click
```
{state.value['click_data']}
```

## hover
```
{state.value['hover_data']}
```

## unhover
```
{state.value['unhover_data']}
```

## deselect
```
{state.value['deselect_data']}
```


"""
    )
