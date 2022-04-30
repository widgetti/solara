from solara.hooks.misc import use_fetch
from solara.kitchensink import react, sol, v

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
    return sol.Div(style_=style, children=children)


@react.component
def App():
    data = use_fetch(json_url)
    json = sol.use_json_load(data)

    with sol.Div() as main:
        if json.error:
            v.Alert(children=[f"Error {json.error}"])
            sol.Button("Retry", on_click=data.retry)
        else:
            if json.value:
                filter = sol.ui_text("", description="Filter pokemons by name")
                pokemons = json.value
                if filter:
                    pokemons = [k for k in pokemons if filter.lower() in k["name"].lower()]
                    v.Label(children=[f"{len(pokemons)} pokemons found"])
                else:
                    v.Label(children=[f"{len(pokemons)} pokemons in total"])
                with Grid(align_items="end", justify_items="stretch"):
                    for pokemon in pokemons[:20]:
                        with sol.Div():
                            name = pokemon["name"]
                            url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/" + pokemon["image"]
                            v.Img(src=url, contain=True, max_height="200px")
                            v.Label(children=[name])
            else:
                with v.Text(children=["Loading..."]):
                    v.ProgressCircular(indeterminate=True, class_="solara-progress")
    return main


app = App()
