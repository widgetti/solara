"""
# Overview
Click on one of the items on the left.
"""

import inspect

import solara
from solara.alias import rv

from .. import List
from .. import SimpleListItem as ListItem

_title = "API"


@solara.component
def Page():
    return solara.Markdown(__doc__)


@solara.component
def Sidebar(children=[], level=0):
    # note that we don't use children here, but we used route.module instead to ge the module
    # this is fine because all api/*.py files use the standard Page component, and do not add
    # a new Layout component
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")

    # keeps track of which routes we includes
    routes = {r.path: r for r in all_routes.copy()}

    def add(path):
        route = routes[path]
        with solara.Link(route):
            ListItem(route.label, class_="active" if route_current is not None and path == route_current.path else None)
        del routes[path]

    # with solara.HBox(grow=True) as main:
    with rv.Col(tag="aside", md=4, lg=3, class_="sidebar bg-grey d-none d-md-block") as main:
        with solara.Head():
            name = route_current.label if route_current.label is not None else "No name"
            if name == "API":
                solara.Title("Solara » API overview")
            else:
                solara.Title("Solara » API » " + name)
        with List():
            add("/")
            with ListItem("Input", icon_name="mdi-chevron-left-box"):
                with List():
                    add("button")
                    add("checkbox")
                    add("input")
                    add("select")
                    add("slider")
                    add("togglebuttons")
                    add("file_browser")
            with ListItem("Output", icon_name="mdi-chevron-right-box"):
                with List():
                    add("markdown")
                    add("markdown_editor")
                    add("html")
                    add("image")
                    # add("code")
                    add("sql_code")
            with ListItem("Status", icon_name="mdi-information"):
                with List():
                    add("success")
                    add("info")
                    add("warning")
                    add("error")
            with ListItem("Viz", icon_name="mdi-chart-histogram"):
                with List():
                    add("altair")
                    add("echarts")
                    add("matplotlib")
                    add("plotly")
                    add("plotly_express")
                #     ListItem("AltairChart")
            with ListItem("Containers", icon_name="mdi-page-layout-sidebar-left"):
                with List():
                    add("hbox")
                    add("vbox")
                    add("griddraggable")
                    add("gridfixed")
                    add("default_layout")
                    # add("app")
            with ListItem("Data", icon_name="mdi-database"):
                with List():
                    # ListItem("DataTable")
                    add("dataframe")
                    # add("pivot_table")
            with ListItem("Page", icon_name="mdi-file-code"):
                with List():
                    add("head")
                    add("title")
            with ListItem("Hooks", icon_name="mdi-hook"):
                with List():
                    # add("use_fetch")
                    # add("use_json")
                    add("use_cross_filter")
                    add("use_thread")
                    add("use_exception")
                    add("use_previous")
                    add("use_state_or_update")
            with ListItem("Types", icon_name="mdi-fingerprint"):
                with List():
                    # ListItem("Action")
                    # ListItem("ColumnAction")
                    # ListItem("Route")
                    add("route")
            with ListItem("Routing", icon_name="mdi-router"):
                with List():
                    add("use_route")
                    add("resolve_path")
                    # add("use_router")
                    # add("use_route_level")

                    # add("resolve_path")
                    # add("use_pathname")

                    # add("generate_routes")
                    # add("generate_routes_directory")

                    # add("RenderPage")
                    # add("DefaultNavigation")
                    add("link")
            with ListItem("Advanced", icon_name="mdi-head-cog-outline"):
                with List():
                    add("style")
            with ListItem("Lab", icon_name="mdi-test-tube"):
                with List():
                    add("cross_filter_report")
                    add("cross_filter_slider")
                    add("cross_filter_select")
        if routes:
            print(f"Routes not used: {list(routes.keys())}")  # noqa

    return main


@solara.component
def Layout(children=[]):
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")

    if route_current.path == "/":
        return solara.Markdown(__doc__)
    else:
        with solara.HBox(grow=True) as main:
            with solara.Padding(4):
                if route_current.module:
                    # we ignore children, and make the element again
                    WithCode(route_current.module)
        return main


@solara.component
def WithCode(module):
    # e = solara.use_exception_handler()
    # if e is not None:
    #     return solara.Error("oops")
    component = getattr(module, "Page", None)
    show_code, set_show_code = solara.use_state(False)
    with rv.Sheet() as main:
        with rv.Dialog(v_model=show_code, on_v_model=set_show_code):
            with rv.Sheet(class_="pa-4"):
                if component:
                    if hasattr(module, "sources"):
                        codes = [inspect.getsource(k) for k in module.sources]
                        code = "\n".join(codes)
                    else:
                        code = inspect.getsource(component.f)
                    code = code.replace("```", "~~~")
                    pre = ""
                    solara.MarkdownIt(
                        f"""
```python
{pre}{code}
```
"""
                    )
        # It renders code better
        solara.Markdown(module.__doc__ or "# no docs yet")
        if component:
            with solara.Card("Example", margin=0, classes=["mt-8"]):
                component()
                solara.Button("Show code", icon_name="mdi-eye", on_click=lambda: set_show_code(True), text=True, class_="mt-8")

                # code = inspect.getsource(module)
                # code_quoted = urllib.parse.quote_plus(code)
                # url = f"https://test.solara.dev/try?code={code_quoted}"
                # solara.Button("Run on solara.dev", icon_name="mdi-pencil", href=url, target="_blank")
    return main
