import dataclasses

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
