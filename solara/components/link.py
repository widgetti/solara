from typing import Union

import ipyvue as vue
import reacton.ipyvue as vuer
import solara


@solara.component
def Link(path_or_route: Union[str, solara.Route], children=[]):
    path = solara.resolve_path(path_or_route, level=0)
    link = vue.Html.element(tag="a", children=children, attributes={"href": path})
    location = solara.use_context(solara.routing._location_context)

    def go(*ignore):
        location.pathname = path

    vuer.use_event(link, "click.prevent.stop", go)
    return link
