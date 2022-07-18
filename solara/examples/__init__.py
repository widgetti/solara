from pathlib import Path

from solara.alias import react, rv, sol
from solara.components.tab_navigation import TabNavigation

directory = Path(__file__).parent
md = open(directory / "README.md").read()

title = "Solara ☀️"

route_order = [
    "/",
    "docs",
    "api",
    "examples",
]


@react.component
def Page():
    # with v.Container(fluid=True):
    with sol.GridFixed(1, justify_items="center") as main:
        sol.Markdown(md)
    return main


@react.component
def Layout(children=[]):
    with sol.VBox(grow=False) as main:
        with rv.AppBar(dark=True, flat=True, color="orange darken-4"):
            rv.ToolbarTitle(children=["☀️ Solara: the web app framework for Python"])
            rv.Spacer()
            sol.Button("GitHub", icon_name="mdi-git", href=sol.github_url, dark=True, target="_blank", text=True)
            rv.Html(tag="span", style_="width: 80px")

        TabNavigation(children=children, dark=True, centered=True, background_color="orange darken-4")
    return main
