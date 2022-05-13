from solara.kitchensink import react, sol, v

from . import calculator, pokemon

tabs = {
    "Calulator": calculator,
    "Pokemon": pokemon,
}


@react.component
def Demo():
    tab, set_tab = react.use_state(0, "tab")

    # md, set_md = use_state("")
    with v.Tabs(v_model=tab, on_v_model=set_tab, vertical=True) as main:
        for key in tabs:
            with v.Tab(children=[key]):
                pass
        module = list(tabs.values())[tab]
        with v.TabsItems(v_model=tab):
            with sol.HBox(grow=False):
                with sol.VBox(grow=False):
                    github_url = sol.util.github_url(module.__file__)
                    with sol.HBox():
                        sol.Button("View on GitHub", icon_name="mdi-github", href=github_url, class_="ma-2", target="_blank")
                    module.App()
    return main
