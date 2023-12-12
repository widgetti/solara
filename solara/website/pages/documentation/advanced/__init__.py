from pathlib import Path

import solara
from solara.autorouting import generate_routes_directory

title = "Advanced"
HERE = Path(__file__)
# if we didn't put the content in the subdirectory, but pointed to the current file
# we would include the current file recursively, causing an infinite loop
routes = generate_routes_directory(HERE.parent / "content")


@solara.component
def Page(route_external=None):
    solara.Markdown(Path(HERE.parent / "content" / "10-howto" / "00-overview.md").read_text())

    with solara.Row(justify="center", style={"flex-wrap": "wrap", "align-items": "start"}):
        for child in route_external.children:
            if child.path == "/":
                continue

            card_title = solara.Link("/documentation/advanced/" + child.path, children=[child.label])

            with solara.Card(title=card_title, style={"min-width": "300px"}):
                with solara.v.List():
                    with solara.v.ListItemGroup():
                        for grandchild in child.children:
                            if grandchild.path == "/":
                                continue
                            with solara.Link(
                                "/documentation/advanced/" + child.path + "/" + grandchild.path
                                if child.path != "/"
                                else "/documentation/advanced/" + grandchild.path
                            ):
                                with solara.v.ListItem():
                                    solara.v.ListItemTitle(children=[grandchild.label])
