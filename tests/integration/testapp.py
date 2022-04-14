import dataclasses

from solara.kitchensink import react, w


@dataclasses.dataclass
class Clicks:
    value: int


@react.component
def ButtonClick():
    clicks, set_clicks = react.use_state(Clicks(0))
    return w.Button(description=f"Clicked {clicks.value} times", on_click=lambda: set_clicks(Clicks(clicks.value + 1)))


app = ButtonClick()
