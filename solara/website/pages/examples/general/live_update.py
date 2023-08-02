from time import sleep

import solara
import numpy as np
from matplotlib import pyplot as plt

# ensure that an interactive backend doesn't start when plotting with matplotlib
plt.switch_backend('agg')


@solara.component
def Page():
    counter = solara.use_reactive(0)

    def render():
        while True:
            sleep(0.2)
            counter.value += 1

    result = solara.use_thread(render)
    if result.error:
        raise result.error
    # force the DataDashboard to redraw, by making it depends on the counter value
    DataDashboard(counter.value)


@solara.component
def DataDashboard(counter):
    fig, ax = plt.subplots()
    ax.plot(np.arange(10), np.random.random(10))
    solara.FigureMatplotlib(fig)


Page()
