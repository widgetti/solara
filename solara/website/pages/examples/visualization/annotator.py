"""# Image annotation with Solara

This example displays how to annotate images with different drawing tools in plotly figures. Use the canvas 
below to draw shapes and visualize the canvas callback.


Check [plotly docs](https://dash.plotly.com/annotations) for more information about image annotation.
"""
import json
import plotly.graph_objects as go

import solara

title = "Plotly Image Annotator"
text = solara.reactive('Draw on canvas')

class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        # Convert object instances to their string representation
        if isinstance(o, object):
            return str(o)
        return super().default(o)

@solara.component
def Page():
    def on_relayout(data):
        if data is None:
            return

        relayout_data = data['relayout_data']

        if "shapes" in relayout_data:
            text.value = str(json.dumps(relayout_data["shapes"], indent=2, cls=CustomEncoder))

    with solara.Div() as main:

        fig = go.FigureWidget(
            layout=go.Layout(
                showlegend=False,
                autosize=False,
                width=600,
                height=600,
                modebar={
                    "add": [
                        "drawclosedpath",
                        "drawcircle",
                        "drawrect",
                        "eraseshape",
                    ]
                }
            )
        )

        solara.FigurePlotly(fig, on_relayout=on_relayout)
        solara.Preformatted(text.value)

    return main
