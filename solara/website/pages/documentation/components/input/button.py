"""
# Button

"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    count, set_count = solara.use_state(0)

    def increment():
        set_count(count + 1)

    with solara.HBox():
        solara.Button(label=f"Clicked {count} times", on_click=increment, icon_name="mdi-thumb-up")


__doc__ += apidoc(solara.Button.f)  # type: ignore
