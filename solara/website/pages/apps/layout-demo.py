import solara
import solara.lab

github_url = solara.util.github_url(__file__)


@solara.component
def Page():
    with solara.Column():
        solara.Title("I'm in the browser tab and the toolbar bar")
        with solara.Sidebar():
            with solara.Card("I am in the sidebar"):
                with solara.Column():
                    solara.SliderInt(label="Ideal for placing controls")
                    solara.Button(
                        label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True
                    )

        solara.Info("I'm in the main content area, put your main content here")
        with solara.Card("Use solara.Columns to create relatively sized columns"):
            with solara.Columns([1, 2]):
                solara.Success("I'm in the first column")
                solara.Warning("I'm in the second column, I am twice as wide")

        with solara.Card("Use solara.Column to create a full width column"):
            with solara.Column():
                solara.Success("I'm first in this full with column")
                solara.Warning("I'm second in this full with column")
                solara.Error("I'm third in this full with column")

        with solara.Card("Use solara.ColumnsResponsive to response to screen size"):
            with solara.ColumnsResponsive(6, large=4):
                for i in range(6):
                    solara.Info("two per column on small screens, three per column on large screens")


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    return solara.AppLayout(children=children)
