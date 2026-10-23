from typing import Any, List

import ipyvuetify
import reacton
import reacton.core
import solara


@reacton.component
def Head(children: List[reacton.core.Element] = []) -> reacton.core.ValueElement[ipyvuetify.Html, Any]:
    """A component that manager the "head" tag of the page to avoid duplicate tags, such as titles.

    Currently only supports the [title](/documentation/components/page/title) tag as child, e.g.:

    ```python
    import solara

    @solara.component
    def Page():
        with solara.VBox() as main:
            MyAwesomeComponent()
            with solara.Head():
                solara.Title("My page title")
        return main

    ```

    """
    return solara.Div(children=children, style="display; none")
