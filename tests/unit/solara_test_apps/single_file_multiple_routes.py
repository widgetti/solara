import solara


@solara.component
def Home():
    with solara.Sidebar():
        solara.SliderInt(label="in sidebar")
    solara.Markdown("Home")


@solara.component
def About():
    solara.Markdown("About")


routes = [
    solara.Route(path="/", component=Home, label="Home"),
    solara.Route(path="about", component=About, label="About"),
]
