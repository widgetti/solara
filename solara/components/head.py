from typing import List

import reacton

import solara


@reacton.component
def Head(children: List[reacton.core.Element] = []):
    """A component that manager the "head" tag of the page to avoid duplicate tags, such as titles.

    Currently only supports the [title](/api/title) tag as child, e.g.:

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
