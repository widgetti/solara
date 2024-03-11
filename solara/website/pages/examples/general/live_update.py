from time import sleep

import numpy as np
from matplotlib import pyplot as plt

import solara


@solara.component
def Page():
    # define some state which will be updated regularly in a separate thread
    counter = solara.use_reactive(0)

    def render():
        """Infinite loop regularly mutating counter state"""
        while True:
            sleep(0.2)
            counter.value += 1

    # run the render loop in a separate thread
    result: solara.Result[bool] = solara.use_thread(render)
    if result.error:
        raise result.error

    # create the LiveUpdatingComponent, this component depends on the counter
    # value so will be redrawn whenever counter value changes
    LiveUpdatingComponent(counter.value)


@solara.component
def LiveUpdatingComponent(counter):
    """Component which will be redrawn whenever the counter value changes."""
    fig, ax = plt.subplots()
    ax.plot(np.arange(10), np.random.random(10))
    solara.FigureMatplotlib(fig)


Page()
