"""Demonstrates how to use Vue components in Solara.

Although many components can be made from the Python side, sometimes it is easier to write components using Vue directly.
It can also be beneficial for performance, since instead of creating many widgets from the Python side we only send data to
the frontend. If event handling is also done on the frontend, this reduces latency and makes you app feel much smoother.

See [the API documentation on component_vue](/api/component_vue) for more information.

This example is based on [the vuetify docs](https://v2.vuetifyjs.com/en/components/sparklines/#custom-labels),
Note that the "Go to report" button does not do anything yet.

"""

from typing import Callable

import numpy as np

import solara

seed = solara.reactive(42)


@solara.component_vue("mycard.vue")
def MyCard(
    event_goto_report: Callable[[dict], None],
    value=[1, 10, 30, 20, 3],
    caption="My Card",
    color="red",
):
    pass


@solara.component
def Page():
    gen = np.random.RandomState(seed=seed.value)
    sales_data = np.floor(np.cumsum(gen.random(7) - 0.5) * 100 + 100)
    show_report = solara.use_reactive(False)

    with solara.Column(style={"min-width": "600px"}):
        if show_report.value:
            with solara.Card("Report"):
                solara.Markdown("Lorum ipsum dolor sit amet")
                solara.Button("Go back", on_click=lambda: show_report.set(False))
        else:

            def new_seed():
                seed.value = np.random.randint(0, 100)

            solara.Button("Generate new data", on_click=new_seed)

            MyCard(value=sales_data.tolist(), color="green", caption="Sales Last 7 Days", event_goto_report=lambda data: show_report.set(True))
