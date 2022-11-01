from typing import Union

import ipyvue as vue
import reacton.ipyvue as vuer

import solara


@solara.component
def Link(
    path_or_route: Union[str, solara.Route],
    children=[],
):
    """Makes clicking on child elements navigate to a route.

    See also:

     * [Multipage](/docs/guides/multipage).
     * [Understanding Routing](/docs/understanding/routing).

    Most common usage is in combination with a button, e.g.:

    ```python
    with solara.Link("/fruit/banana"):
        solara.Button("Go to banana")
    ```


    ## Arguments

     * path_or_route: the path or route to navigate to. Paths should be absolute, e.g. '/fruit/banana'.
       If a route is given, [`resolve_path`](/api/resolve_path)] will be used to resolve to the absolute path.
     * children: the children of the link. If a child is clicked, the link will be followed.

    """
    path = solara.resolve_path(path_or_route, level=0)
    link = vue.Html.element(tag="a", children=children, attributes={"href": path})
    location = solara.use_context(solara.routing._location_context)

    def go(*ignore):
        location.pathname = path

    vuer.use_event(link, "click.prevent.stop", go)
    return link
