from typing import Dict, List, Union

import ipyvue as vue
import reacton.ipyvue as vuer

import solara


@solara.component
def Link(
    path_or_route: Union[str, solara.Route],
    children=[],
    nofollow=False,
    style: Union[str, Dict[str, str], None] = None,
    classes: List[str] = [],
):
    """Makes clicking on child elements navigate to a route.

    See also:

     * [Multipage](/docs/howto/multipage).
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
     * nofollow: If True, the link will not be followed by web crawlers (such as google).
     * style: CSS styles to apply to the HTML link element. Either a string or a dictionary.
     * classes: A list of CSS classes to apply to the link.

    """
    path = solara.resolve_path(path_or_route, level=0)
    attributes = {"href": path}
    if nofollow:
        attributes["rel"] = "nofollow"
    style_flat = solara.util._flatten_style(style)
    classes_flat = solara.util._combine_classes(classes)

    link = vue.Html.element(tag="a", children=children, attributes=attributes, style_=style_flat, class_=classes_flat)
    location = solara.use_context(solara.routing._location_context)

    def go(*ignore):
        location.pathname = path

    vuer.use_event(link, "click.prevent.stop", go)
    return link
