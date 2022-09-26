from typing import Union

import ipyvue as vue
import reacton
import reacton.ipyvue as vuer

import solara as sol


@reacton.component
def Link(path_or_route: Union[str, sol.Route], children=[]):
    path = sol.resolve_path(path_or_route, level=0)
    link = vue.Html.element(tag="a", children=children, attributes={"href": path})
    location = reacton.use_context(sol.routing._location_context)

    def go(*ignore):
        location.pathname = path

    vuer.use_event(link, "click.prevent.stop", go)
    return link
