"""
# use_query_parameter

"""

import solara
from solara.website.utils import apidoc

title = "use_query_parameter"


@solara.component
def Page():
    count, set_count = solara.use_query_parameter("count", 2, int)
    if count > 0:
        solara.Text("👍" * count)
    if count == 0:
        solara.Text("🤔")
    else:
        solara.Text("👎" * (-count))
    solara.Button("Increment", on_click=lambda: set_count(count + 1))
    solara.Button("Decrement", on_click=lambda: set_count(count - 1))


__doc__ += apidoc(solara.use_query_parameter)  # type: ignore
