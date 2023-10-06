"""# Image annotation with Solara

This example displays how to annotate images with different drawing tools in plotly figures. Use the canvas
below to draw shapes and visualize the canvas callback.


Check [plotly docs](https://dash.plotly.com/annotations) for more information about image annotation.
"""
import json

import plotly.graph_objects as go

import solara

title = "Plotly Image Annotator"
shapes = solara.reactive(None)


class CustomEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for Plotly objects.

    Plotly may return objects that the standard JSON encoder can't handle. This
    encoder converts such objects to str, allowing serialization by json.dumps
    """

    def default(self, o):
        if isinstance(o, object):
            return str(o)
        return super().default(o)


@solara.component
def Page():
    def on_relayout(data):
        if data is None:
            return

        relayout_data = data["relayout_data"]

        if "shapes" in relayout_data:
            shapes.value = relayout_data["shapes"]

    fig = go.FigureWidget(
        layout=go.Layout(
            showlegend=False,
            autosize=False,
            width=600,
            height=600,
            dragmode="drawrect",
            modebar={
                "add": [
                    "drawclosedpath",
                    "drawcircle",
                    "drawrect",
                    "eraseshape",
                ]
            },
        )
    )

    solara.FigurePlotly(fig, on_relayout=on_relayout)
    if not shapes.value:
        solara.Markdown("## Draw on the canvas")
    else:
        solara.Markdown("## Data returned by drawing")
        formatted_shapes = str(json.dumps(shapes.value, indent=2, cls=CustomEncoder))
        solara.Preformatted(formatted_shapes)
