from solara.kitchensink import react, v


@react.component
def ColorCard(title, color):
    with v.Card(style_=f"background-color: {color}; width: 100%; height: 100%") as main:
        v.CardTitle(children=[title])
    return main
