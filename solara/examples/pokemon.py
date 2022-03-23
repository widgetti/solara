from solara.kitchensink import *


json_url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/index.json"


@react.component
def Grid(columns=4, column_gap="10px", row_gap="10px", children=[], align_items="stretch", justify_items="stretch"):
    """

    See css grid spec:
    https://css-tricks.com/snippets/css/complete-guide-grid/
    """
    style = (
        f"display: grid; grid-template-columns: repeat({columns}, minmax(0, 1fr)); "
        + f"grid-column-gap: {column_gap}; grid-row-gap: {row_gap}; align-items: {align_items}; justify-items: {justify_items}"
    )
    return Div(style_=style, children=children)
    # v.Container()


@react.component
def Img(children=[], **kwargs):
    return vue.Html.element(tag="img", children=children, **kwargs)


from IPython.display import Javascript, display


@react.component
def App():
    json, error = use_json(json_url)
    print(display, display.__module__)
    import altair as alt
    import pandas as pd

    source = pd.DataFrame({"a": ["A", "B", "C", "D", "E", "F", "G", "H", "I"], "b": [28, 55, 43, 91, 81, 53, 19, 87, 52]})

    a = alt.Chart(source).mark_bar().encode(x="a", y="b")
    with Div() as main:
        if error:
            v.Alert(children=[f"Error {error}"])
        else:
            if json:
                filter = ui_text("", description="Filter pokemons by name")
                pokemons = json
                if filter:
                    pokemons = [k for k in pokemons if filter.lower() in k["name"].lower()]
                    v.Label(children=f"{len(pokemons)} pokemons found")
                else:
                    v.Label(children=f"{len(pokemons)} pokemons in total")
                with Grid(align_items="end", justify_items="stretch"):
                    for pokemon in pokemons[:20]:
                        with Div():
                            name = pokemon["name"]
                            url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/" + pokemon["image"]
                            v.Img(src=url, contain=True, max_height="200px")
                            v.Label(children=[name])
            else:
                v.Alert(children=["Loading..."])
    return main


app = App()
