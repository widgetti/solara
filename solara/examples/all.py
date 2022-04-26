from pathlib import Path
from typing import cast

from solara.kitchensink import react, sol, v

from .components import Components
from .demo import Demo
from .doc import Doc
from .libraries import Libraries

directory = Path(__file__).parent

md = open(directory / "README.md").read()


@react.component
def Home():
    with sol.Div() as main:
        sol.Markdown(md)
    return main


routes = [
    dict(component=Home, path="/", label="What is Solara ☀️?"),
    dict(component=Libraries, path="/libraries", label="Supported libraries"),
    dict(component=Demo, path="/demo", label="Demo"),
    dict(component=Components, path="/components", label="Components"),
    dict(component=Doc, path="/doc", label="Docs"),
]


@react.component
def All():
    tab, set_tab = react.use_state(0, "tab")

    route_current = routes[tab]
    path = route_current["path"]

    def on_location(location: str):
        matching_tabs = [tab for tab, route in enumerate(routes) if route["path"] == location]
        if matching_tabs:
            set_tab(matching_tabs[0])

    with v.Tabs(v_model=tab, on_v_model=set_tab) as main:
        sol.Navigator(location=path, on_location=on_location)

        for route in routes:
            with v.Tab(children=[route["label"]]):
                pass
        with v.TabsItems(v_model=tab):
            component = cast(react.core.Component, route_current["component"])
            key = key = route_current["path"]
            component().key(f"path_{key}")

    return main


app = All()
