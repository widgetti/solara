"""# Interactive sine wave


This example shows how to have two slider control a visualization.

"""

import numpy as np
import plotly.express as px

import solara

x = np.linspace(0, 2, 100)

title = "Interactive sine wave"
freq = solara.reactive(2.0)
phase = solara.reactive(0.1)


@solara.component
def Page():
    y = np.sin(x * freq.value + phase.value)

    solara.FloatSlider("Frequency", value=freq, min=0, max=10)
    solara.FloatSlider("Phase", value=phase, min=0, max=np.pi, step=0.1)

    fig = px.line(x=x, y=y)
    solara.FigurePlotly(fig)
