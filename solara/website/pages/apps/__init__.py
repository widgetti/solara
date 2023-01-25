import solara


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    return solara.AppLayout(children=children)
    return solara.AppLayout(children=children)
