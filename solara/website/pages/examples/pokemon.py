from solara.alias import reacton, rv, sol
from solara.hooks.misc import use_fetch

github_url = sol.util.github_url(__file__)

json_url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/index.json"


@reacton.component
def Page():
    data = use_fetch(json_url)
    json = sol.use_json_load(data)

    with sol.Div() as main:
        if json.error:
            rv.Alert(children=[f"Error {json.error}"])
            sol.Button("Retry", on_click=data.retry)
        else:
            if json.value:
                filter = sol.ui_text(label="Filter pokemons by name", value="")
                pokemons = json.value
                if filter:
                    pokemons = [k for k in pokemons if filter.lower() in k["name"].lower()]
                    rv.Label(children=[f"{len(pokemons)} pokemons found"])
                else:
                    rv.Label(children=[f"{len(pokemons)} pokemons in total"])
                with sol.GridFixed(columns=4, align_items="end", justify_items="stretch"):
                    for pokemon in pokemons[:20]:
                        with sol.Div():
                            name = pokemon["name"]
                            url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/" + pokemon["image"]
                            rv.Img(src=url, contain=True, max_height="200px")
                            rv.Label(children=[name])
            else:
                with sol.Div():
                    sol.Text("Loading...")
                    rv.ProgressCircular(indeterminate=True, class_="solara-progress")
    return main
