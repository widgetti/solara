import solara
from solara.alias import rv
from solara.hooks.misc import use_fetch

github_url = solara.util.github_url(__file__)

json_url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/index.json"


@solara.component
def Page():
    data = use_fetch(json_url)
    json = solara.use_json_load(data)

    with solara.Div() as main:
        if json.error:
            rv.Alert(children=[f"Error {json.error}"])
            solara.Button("Retry", on_click=data.retry)
        else:
            if json.value:
                filter = solara.ui_text(label="Filter pokemons by name", value="")
                pokemons = json.value
                if filter:
                    pokemons = [k for k in pokemons if filter.lower() in k["name"].lower()]
                    rv.Label(children=[f"{len(pokemons)} pokemons found"])
                else:
                    rv.Label(children=[f"{len(pokemons)} pokemons in total"])
                with solara.GridFixed(columns=4, align_items="end", justify_items="stretch"):
                    for pokemon in pokemons[:20]:
                        with solara.Div():
                            name = pokemon["name"]
                            url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/" + pokemon["image"]
                            rv.Img(src=url, contain=True, max_height="200px")
                            rv.Label(children=[name])
            else:
                with solara.Div():
                    solara.Text("Loading...")
                    rv.ProgressCircular(indeterminate=True, class_="solara-progress")
    return main
