import dataclasses

import solara
from solara.alias import rw


@dataclasses.dataclass
class Clicks:
    value: int


@solara.component
def ButtonClick():
    clicks, set_clicks = solara.use_state(Clicks(0))
    return rw.Button(description=f"Clicked {clicks.value} times", on_click=lambda: set_clicks(Clicks(clicks.value + 1)))
