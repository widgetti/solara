import dataclasses
import os

import ipyvue
import traitlets

from solara.kitchensink import react, sol, w


@dataclasses.dataclass
class Clicks:
    value: int


@react.component
def ButtonClick():
    clicks, set_clicks = react.use_state(Clicks(0))
    return w.Button(description=f"Clicked {clicks.value} times", on_click=lambda: set_clicks(Clicks(clicks.value + 1)))


app = ButtonClick()


@react.component
def ClickBoom():
    count, set_count = react.use_state(0)
    if count == 1:
        raise ValueError("I crash on 1")
    return sol.Button("Boom", on_click=lambda: set_count(count + 1))


clickboom = ClickBoom()


class TestWidget(ipyvue.VueTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "test.vue"))

    value = traitlets.Any(0).tag(sync=True)


@react.component
def VueTestApp():
    return TestWidget.element(value="foobar")


vue_test_app = VueTestApp()
