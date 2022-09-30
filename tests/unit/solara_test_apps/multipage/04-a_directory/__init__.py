import solara


@solara.component
def Layout(children=[]):
    with solara.VBox(children=children) as main:
        solara.Info("Footer")
    return main
