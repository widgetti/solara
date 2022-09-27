"""# Matplotlib

"""

import numpy as np
from matplotlib.figure import Figure

from solara.alias import reacton, sol
from solara.website.utils import apidoc

x = np.linspace(0, 2, 100)


@reacton.component
def Page():
    freq, set_freq = reacton.use_state(2.0)
    phase, set_phase = reacton.use_state(0.1)
    y = np.sin(x * freq + phase)

    fig = Figure()
    ax = fig.subplots()
    ax.plot(x, y)
    ax.set_ylim(-1.2, 1.2)

    with sol.VBox() as main:
        sol.FloatSlider("Frequency", value=freq, on_value=set_freq, min=0, max=10)
        sol.FloatSlider("Phase", value=phase, on_value=set_phase, min=0, max=np.pi, step=0.1)
        sol.FigureMatplotlib(fig, dependencies=[freq, phase])
    return main


__doc__ += apidoc(sol.FigureMatplotlib.f)  # type: ignore
