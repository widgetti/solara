"""# Matplotlib

"""

import numpy as np
import solara
from matplotlib.figure import Figure
from solara.website.utils import apidoc

x = np.linspace(0, 2, 100)


@solara.component
def Page():
    freq, set_freq = solara.use_state(2.0)
    phase, set_phase = solara.use_state(0.1)
    y = np.sin(x * freq + phase)

    fig = Figure()
    ax = fig.subplots()
    ax.plot(x, y)
    ax.set_ylim(-1.2, 1.2)

    with solara.VBox() as main:
        solara.FloatSlider("Frequency", value=freq, on_value=set_freq, min=0, max=10)
        solara.FloatSlider("Phase", value=phase, on_value=set_phase, min=0, max=np.pi, step=0.1)
        solara.FigureMatplotlib(fig, dependencies=[freq, phase])
    return main


__doc__ += apidoc(solara.FigureMatplotlib.f)  # type: ignore
