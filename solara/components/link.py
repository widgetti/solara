from typing import Union

import ipyvue as vue
import react_ipywidgets as react
import react_ipywidgets.ipyvue as vuer

import solara as sol


@react.component
def Link(path_or_route: Union[str, sol.Route], children=[]):
    path = sol.resolve_path(path_or_route, level=0)
    link = vue.Html.element(tag="a", children=children, attributes={"href": path})
    location = react.use_context(sol.routing._location_context)

    def go(*ignore):
        location.pathname = path

    vuer.use_event(link, "click.prevent.stop", go)
    return link
