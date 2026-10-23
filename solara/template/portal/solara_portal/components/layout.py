import solara


@solara.component
def Layout(children=[]):
    return solara.VBox(children=children)
