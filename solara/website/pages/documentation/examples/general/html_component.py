"""Native HTML components with scoped CSS, Python bindings, and composition.

The `greeting.html` file contains the template, style, and optional browser code.
The page uses the normal Solara app shell; the greeting itself has a native
Shadow DOM view and does not use a Vue template.

The input's `data-solara-model="name"` changes the synchronized `name` prop
and calls Python's `on_name`. The button's `data-solara-event-click="reset"`
calls the separate `event_reset` action. The former is the native HTML
equivalent of changing a prop directly in a Solara Vue component.

See [component_html](/documentation/api/utilities/component_html) for the full API.
"""

import solara


@solara.component_html("greeting.html")
def Greeting(name="World", on_name=None, event_reset=None, children=None):
    pass


@solara.component_html("native_button.html")
def NativeButton(label="Choose Ada", event_click=None):
    pass


@solara.component
def Page():
    name, set_name = solara.use_state("World")
    Greeting(
        name=name,
        on_name=set_name,
        event_reset=lambda _data: set_name("World"),
        children=[NativeButton(label="Choose Ada", event_click=lambda _data: set_name("Ada"))],
    )
