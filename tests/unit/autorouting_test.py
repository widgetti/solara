from pathlib import Path

import ipyvuetify as v
import ipywidgets as widgets

import solara
import solara.autorouting
import solara.template.portal.solara_portal.pages
import solara.website.pages.api.button
import solara.website.pages.docs
import solara.website.pages.examples
import solara.widgets
from solara.components.title import TitleWidget

HERE = Path(__file__)


def test_count_arguments():
    def f1(a, b):
        pass

    assert solara.autorouting.count_arguments(f1) == 2

    def f2(a, b, c=1):
        pass

    assert solara.autorouting.count_arguments(f2) == 2

    def f3(a, b, c=None):
        pass

    assert solara.autorouting.count_arguments(f3) == 2

    def f4(a, b, c=None, *args):
        pass

    assert solara.autorouting.count_arguments(f4) == 2

    def f5(a, b, c=None, **kwargs):
        pass

    assert solara.autorouting.count_arguments(f5) == 2


def test_cast():
    def f1(a, b):
        pass

    assert solara.autorouting.arg_cast(["a", "b"], f1) == ["a", "b"]

    def f2(a, b: int):
        pass

    assert solara.autorouting.arg_cast(["a", "42"], f2) == ["a", 42]

    @solara.component
    def F3(a, b: int):
        pass

    assert solara.autorouting.arg_cast(["a", "42"], F3) == ["a", 42]


def test_routes_portal():
    routes = solara.autorouting.generate_routes(solara.template.portal.solara_portal.pages)

    assert routes[0].path == "/"
    assert routes[1].path == "article"
    assert routes[2].path == "tabular"
    assert routes[3].path == "viz"
    assert routes[3].children[0].path == "/"

    main_object = solara.autorouting.RenderPage()
    root = solara.RoutingProvider(routes=routes, pathname="/", children=[main_object])

    container, rc = solara.render(root, handle_error=False)
    nav = rc._find(solara.widgets.Navigator).widget
    title = rc._find(TitleWidget)[-1].widget
    assert title.title == "Solara demo » Home"
    assert rc._find(v.ToolbarTitle).widget.children[0] == "Solara demo » Home"
    nav.location = "/tabular/titanic"
    title = rc._find(TitleWidget)[-1].widget
    assert "titanic" in title.title

    nav.location = "/viz/scatter/titanic"
    title = rc._find(TitleWidget)[-1].widget
    assert "titanic" in title.title
    assert "scatter" in title.title


def test_routes_examples_api_button():
    routes = solara.autorouting.generate_routes(solara.website.pages.api.button)

    assert len(routes) == 1
    assert routes[0].path == "/"

    main_object = solara.autorouting.RenderPage()
    solara_context = solara.RoutingProvider(children=[main_object], routes=routes, pathname="/")

    container, rc = solara.render(solara_context, handle_error=False)

    assert not rc._find(v.NavigationDrawer)


def test_routes_examples_docs():
    routes = solara.autorouting.generate_routes(solara.website.pages.docs)

    assert len(routes) == 16
    assert routes[0].path == "/"
    assert routes[0].label == "Introduction"

    main_object = solara.autorouting.RenderPage()
    solara_context = solara.RoutingProvider(children=[main_object], routes=routes, pathname="/")

    container, rc = solara.render(solara_context, handle_error=False)

    rc._find(v.AppBar).assert_not_empty()


# requires altair as dependency
# def test_routes_examples_examples():

#     routes = solara.autorouting.generate_routes(solara.website.pages)

#     assert len(routes) > 1

#     main_object = solara.autorouting.RenderPage()
#     solara_context = solara.RoutingProvider(children=[main_object], routes=routes, pathname="/")

#     container, rc = solara.render(solara_context, handle_error=False)
#     nav = rc._find(solara.widgets.Navigator).widget
#     nav.location = "/examples/calculator"
#     assert rc._find(v.Tabs, vertical=True)


def test_routes_directory():
    routes = solara.autorouting.generate_routes_directory(HERE.parent / "solara_test_apps" / "multipage")
    assert len(routes) == 8
    assert routes[0].path == "/"
    assert routes[0].label == "Home"

    assert routes[1].path == "my-fruit"
    assert routes[1].label == "My Fruit"
    assert routes[1].children

    assert routes[2].path == "some-markdown"
    assert routes[2].label == "Some Markdown"

    assert routes[3].path == "a-directory"
    assert routes[3].label == "A Directory"
    assert len(routes[3].children) == 2

    assert routes[4].path == "and-notebooks"
    assert routes[4].label == "And Notebooks"

    assert routes[5].path == "custom-routes"
    assert routes[5].label == "Custom Routes"
    assert routes[5].children[0].path == "/"
    assert routes[5].children[0].label == "Hi1"
    assert routes[5].children[1].path == "page2"
    assert routes[5].children[1].label == "Hi2"

    assert routes[6].path == "single-file-directory"
    assert routes[6].label == "Single File Directory"

    assert routes[7].path == "some-other-python-script"
    assert routes[7].label == "Some Other Python Script"

    main_object = solara.autorouting.RenderPage()
    solara_context = solara.RoutingProvider(children=[main_object], routes=routes, pathname="/")

    container, rc = solara.render(solara_context, handle_error=False)
    nav = rc._find(solara.widgets.Navigator).widget
    title = rc._find(TitleWidget).widget
    assert title.title == "Home"

    nav.location = "/my-fruit"
    title = rc._find(TitleWidget).widget
    assert "My Fruit" == title.title

    nav.location = "/some-markdown"
    title = rc._find(TitleWidget).widget
    assert "Some Markdown" == title.title
    template = rc._find(v.VuetifyTemplate)[-1].widget
    assert "renders to highlighted Python code" in template.template

    nav.location = "/some-other-python-script"
    alert = rc._find(v.Alert).widget
    assert "No object with name Page found" in alert.children[0]

    nav.location = "/a-directory"
    title = rc._find(TitleWidget).widget
    assert "Another Markdown" == title.title
    alert = rc._find(v.Alert).widget
    assert "Footer" == alert.children[0]

    nav.location = "/and-notebooks"
    assert rc._find(v.Slider, label="Language")

    # test navigation in single file directory
    nav.location = "/single-file-directory"
    title = rc._find(TitleWidget).widget
    assert "Single File" == title.title
    assert len(rc._find(v.AppBar)) == 1

    nav.location = "/wrong-path"
    assert "Page not found" in rc._find(v.Alert).widget.children[0]

    nav.location = "/a-directory/wrong-path"
    assert "Page not found" in rc._find(v.Alert).widget.children[0]

    # custom routes in a single file

    nav.location = "/custom-routes"
    button = rc._find(v.Btn, children=["hi1"]).widget
    assert button.children[0] == "hi1"

    nav.location = "/custom-routes/page2"
    button = rc._find(v.Btn, children=["hi2"]).widget
    assert button.children[0] == "hi2"


def test_routes_regular_widgets():
    # routes = solara.autorouting.generate_routes_directory(HERE.parent / "solara_test_apps" / "multipage")
    routes = solara.autorouting.generate_routes_directory(HERE.parent / "solara_test_apps" / "multipage-widgets")

    main_object = solara.autorouting.RenderPage()
    solara_context = solara.RoutingProvider(children=[main_object], routes=routes, pathname="/")

    container, rc = solara.render(solara_context, handle_error=False)
    nav = rc.find(solara.widgets.Navigator).widget

    html = rc.find(v.VuetifyTemplate)[-1].widget
    assert "regular ipywidget" in html.template

    nav.location = "/views"
    rc.find(widgets.Button, description="Never viewed").widget.click()
    assert rc.find(widgets.Button).widget.description == "Viewed 1 times"

    nav.location = "/likes"
    rc.find(widgets.Button, description="No likes recorded").widget.click()
    rc.find(widgets.Button, description="Liked 1 times").widget.click()
    rc.find(widgets.Button, description="Liked 2 times").widget.click()

    # if we navigate back, the state should be preserved for regular ipywidgets
    nav.location = "/views"
    assert rc.find(widgets.Button).widget.description == "Viewed 1 times"

    # but not for elements
    nav.location = "/volume"
    assert rc.find(v.Slider).widget.v_model == 5
    rc.find(v.Slider).widget.v_model = 11
    nav.location = "/views"
    assert rc.find(widgets.Button).widget.description == "Viewed 1 times"
    nav.location = "/volume"
    assert rc.find(v.Slider).widget.v_model == 5
