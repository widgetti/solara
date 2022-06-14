from solara.kitchensink import react, sol


@react.component
def Layout(children=[]):
    return sol.VBox(children=children)
