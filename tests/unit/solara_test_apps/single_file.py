import solara


@solara.component
def Page():
    with solara.Sidebar():
        solara.SliderInt(label="in sidebar")
    solara.Markdown("Home")
