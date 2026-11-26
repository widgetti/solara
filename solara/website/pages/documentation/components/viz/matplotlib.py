"""# Matplotlib"""

import numpy as np
from matplotlib.figure import Figure

import solara
from solara.website.utils import apidoc

x = np.linspace(0, 2, 100)


@solara.component
def Page():
    freq = solara.use_reactive(2.0)
    phase = solara.use_reactive(0.1)
    y = np.sin(x * freq + phase)

    fig = Figure()
    ax = fig.subplots()
    ax.plot(x, y)
    ax.set_ylim(-1.2, 1.2)

    solara.FloatSlider("Frequency", value=freq.value, on_value=lambda v: setattr(freq, "value", v), min=0, max=10)
    solara.FloatSlider("Phase", value=phase.value, on_value=lambda v: setattr(phase, "value", v), min=0, max=np.pi, step=0.1)
    solara.FigureMatplotlib(fig, dependencies=[freq, phase])


__doc__ += apidoc(solara.FigureMatplotlib.f)  # type: ignore
