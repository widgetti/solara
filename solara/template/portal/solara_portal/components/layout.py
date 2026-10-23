from typing import Any

import ipyvuetify
import reacton.core
import solara


@solara.component
def Layout(children=[]) -> reacton.core.ValueElement[ipyvuetify.Sheet, Any]:
    return solara.VBox(children=children)
