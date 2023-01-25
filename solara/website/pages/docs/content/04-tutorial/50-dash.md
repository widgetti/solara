# Tutorial: Dash users

Dash is quite different from Solara. In Dash, state lives in your browser, and via callbacks your app will change from 1 state to another. In Solara, the state lives on the server, and also state transitions happen at the server.
  <!-- * memory
  * spin up/down
  *  -->
<!-- Dash will scale better to many users than Solara, when you app is not doing much work. However, if you app is doing some CPU intensive work (as many data apps do), the benefit of having state at the frontend is not significant any more. -->

## Dash example
To see how Dash and Solara are different, let us start with a typical Dash example:

```python
from dash import Dash, Input, Output, callback, dcc, html

app = Dash(__name__)

app.layout = html.Div(
    children=[
        dcc.Dropdown(id="dropdown", options=["red", "green", "blue", "orange"]),
        dcc.Markdown(id="markdown", children=["## Hello World"]),
    ]
)


@callback(
    Output("markdown", "style"),
    Input("dropdown", "value"),
)
def update_markdown_style(color):
    return {"color": color}


if __name__ == "__main__":
    app.run_server(debug=True)
```

*This example is inspired on [a dash example](https://dash.plotly.com/all-in-one-components).*

This small app creates a dropdown (what we call Select in Solara), and some markdown text. The dropdown will trigger the callback at the server, which will update the markdown's style, which will cause the color of the text to change.

## Translated to Solara

In Solara, we need to explicitly create state using `use_state`. We wire this up with the [Select][/api/select] via `value=color, on_value=set_color` and pass the color down to the [Markdown](/api/markdown) component.

```solara
import solara


@solara.component
def Page():
    color, set_color = solara.use_state("red")
    solara.Select(label="Color",values=["red", "green", "blue", "orange"],
                    value=color, on_value=set_color)
    solara.Markdown("## Hello World", style={"color": color})

```

Since this component combines two components, we have to put them together in a [container](/docs/understanding/containers) component, here a [Column](/api/column).

## Making a re-usable component

### In dash

Following the [All in one component documentation](https://dash.plotly.com/all-in-one-components), we get:

```python
import uuid

from dash import MATCH, Dash, Input, Output, State, callback, dcc, html


class MarkdownWithColorAIO(html.Div):
    class ids:
        dropdown = lambda aio_id: {"component": "MarkdownWithColorAIO", "subcomponent": "dropdown", "aio_id": aio_id}
        markdown = lambda aio_id: {"component": "MarkdownWithColorAIO", "subcomponent": "markdown", "aio_id": aio_id}

    ids = ids

    def __init__(self, text, colors=None, markdown_props=None, dropdown_props=None, aio_id=None):
        colors = colors if colors else ["red", "green", "blue", "orange"]

        if aio_id is None:
            aio_id = str(uuid.uuid4())

        dropdown_props = dropdown_props.copy() if dropdown_props else {}
        if "options" not in dropdown_props:
            dropdown_props["options"] = [{"label": i, "value": i} for i in colors]
        dropdown_props["value"] = dropdown_props["options"][0]["value"]

        markdown_props = markdown_props.copy() if markdown_props else {}
        if "style" not in markdown_props:
            markdown_props["style"] = {"color": dropdown_props["value"]}
        if "children" not in markdown_props:
            markdown_props["children"] = text
        super().__init__([dcc.Dropdown(id=self.ids.dropdown(aio_id), **dropdown_props), dcc.Markdown(id=self.ids.markdown(aio_id), **markdown_props)])

    @callback(
        Output(ids.markdown(MATCH), "style"),
        Input(ids.dropdown(MATCH), "value"),
        State(ids.markdown(MATCH), "style"),
    )
    def update_markdown_style(color, existing_style):
        existing_style["color"] = color
        return existing_style


app = Dash(__name__)

app.layout = html.Div(
    children=[
        MarkdownWithColorAIO("## Hello World1"),
        MarkdownWithColorAIO("## Hello World2"),
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)

```

### In Solara

In Solara, a component is directly reusable. We will rename (from `Page` to `MarkdownWithColor`) the component, and put
in the markdown text as an argument.

```solara
import solara


@solara.component
def MarkdownWithColor(markdown_text : str):
    color, set_color = solara.use_state("red")
    solara.Select(label="Color",values=["red", "green", "blue", "orange"],
                    value=color, on_value=set_color)
    solara.Markdown(markdown_text, style={"color": color})


@solara.component
def Page():
    with solara.Columns():
        MarkdownWithColor("## Re-use is simple")
        MarkdownWithColor("## With solara")
```
