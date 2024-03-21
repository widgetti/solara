"""# Pokemon search

This example shows to to dynamically fetch data and render the results in a table when done, and show an error on failure.

It also shows an optional filter to narrow down the results.
"""

import solara
from solara import use_fetch
from solara.alias import rv

github_url = solara.util.github_url(__file__)

json_url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/index.json"


@solara.component
def Page():
    data = use_fetch(json_url)
    json = solara.use_json_load(data)
    filter, set_filter = solara.use_state("")

    with solara.Div() as main:
        if json.error:
            solara.Error(f"Error {json.error}")
            solara.Button("Retry", on_click=data.retry)
        else:
            if json.value:
                solara.InputText(label="Filter pokemons by name", value=filter, on_value=set_filter, continuous_update=True)
                pokemons = json.value
                if filter:
                    pokemons = [k for k in pokemons if filter.lower() in k["name"].lower()]
                    if len(pokemons) == 0:
                        solara.Warning("No pokemons found, try a different filter")
                    else:
                        solara.Info(f"{len(pokemons)} pokemons found")
                else:
                    solara.Info(f"{len(pokemons)} pokemons in total")
                with solara.GridFixed(columns=4, align_items="end", justify_items="stretch"):
                    for pokemon in pokemons[:20]:
                        with solara.Div():
                            name = pokemon["name"]
                            url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/" + pokemon["image"]
                            # TODO: how to do this with solara
                            rv.Img(src=url, contain=True, max_height="200px")
                            solara.Text(name)
            else:
                with solara.Div():
                    solara.Text("Loading...")
                    rv.ProgressCircular(indeterminate=True, class_="solara-progress")
    return main
