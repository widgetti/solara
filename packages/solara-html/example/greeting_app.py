import solara

import solara_html


@solara_html.component_html("greeting.html")
def Greeting(name="World", on_name=None, event_reset=None, children=[]):
    pass


name = solara.reactive("World")


@solara.component
def Page():
    with solara.Column(style={"padding": "1rem"}):
        # A regular (Vue) Solara component, projected into the template's <slot>.
        with Greeting(name=name.value, on_name=name.set, event_reset=lambda _data: name.set("World")):
            solara.Button("Shout", on_click=lambda: name.set(name.value.upper()))
        solara.Markdown(f"Python sees: **{name.value}**")
