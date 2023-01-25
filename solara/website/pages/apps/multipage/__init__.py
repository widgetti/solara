import solara

github_url = solara.util.github_url(__file__)


@solara.component
def Page():
    with solara.Sidebar():
        solara.Markdown("This is the sidebar at the home page11!")
    with solara.Card("Home"):
        solara.Markdown("This is the home page")
        solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    return solara.AppLayout(children=children)
