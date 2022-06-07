import inspect
import urllib.parse

from solara.kitchensink import react, sol, v

from . import calculator, pokemon, sine

tabs = {
    "Sine": sine,
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
                        sol.Button("View on GitHub", icon_name="mdi-git", href=github_url, class_="ma-2", target="_blank")
                        code = inspect.getsource(module)

                        code_quoted = urllib.parse.quote_plus(code)
                        url = f"https://test.solara.dev/try?code={code_quoted}"
                        sol.Button("Run on solara.dev", icon_name="mdi-pencil", href=url, class_="ma-2", target="_blank")

                    module.App()
    return main
