import numpy as np
import plotly.express as px

from solara.kitchensink import react, sol

x = np.linspace(0, 2, 100)


@react.component
def App():
    freq, set_freq = react.use_state(2.0)
    phase, set_phase = react.use_state(0.1)
    y = np.sin(x * freq + phase)

    with sol.VBox() as main:
        sol.FloatSlider("Frequency", value=freq, on_value=set_freq, min=0, max=10)
        sol.FloatSlider("Phase", value=phase, on_value=set_phase, min=0, max=np.pi, step=0.1)

        fig = px.line(x=x, y=y)
        sol.FigurePlotly(fig)
    return main


app = App()
