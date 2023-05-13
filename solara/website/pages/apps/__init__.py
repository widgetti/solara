import solara


@solara.component
def Page():
    solara.Markdown(
        """
    Hi there 👋! All fullscreen apps are linked from [the examples page](/examples).
    """
    )


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    return children[0]
