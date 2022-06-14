from solara.kitchensink import react, sol


@react.component
def Layout(children=[]):
    with sol.VBox(children=children) as main:
        sol.Info("Footer")
    return main
