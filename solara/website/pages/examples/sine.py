import numpy as np
import plotly.express as px
import solara

x = np.linspace(0, 2, 100)


@solara.component
def Page():
    freq, set_freq = solara.use_state(2.0)
    phase, set_phase = solara.use_state(0.1)
    y = np.sin(x * freq + phase)

    with solara.VBox() as main:
        solara.FloatSlider("Frequency", value=freq, on_value=set_freq, min=0, max=10)
        solara.FloatSlider("Phase", value=phase, on_value=set_phase, min=0, max=np.pi, step=0.1)

        fig = px.line(x=x, y=y)
        solara.FigurePlotly(fig)
    return main
