from pathlib import Path

import solara
from solara.website.components.sidebar import Sidebar

_title = "Documentation"

HERE = Path(__file__).parent
Sidebar = Sidebar

route_order = ["/", "getting_started", "examples", "components", "api", "advanced", "faq"]


@solara.component_vue(str(HERE.parent.parent / "components" / "algolia_api.vue"))
def Algolia():
    pass


@solara.component
def Page(children=[]):
    # show a gallery of all the api pages
    router = solara.use_router()
    route_current = router.path_routes[-2]

    with solara.Column(style={"width": "100%"}, gap="75px"):
        if route_current.path == "documentation":
            with solara.Column(classes=["api-search-container"], gap="50px", style={"justify-content": "center"}, align="center"):
                solara.Markdown("# Search the Solara Documentation", style={"text-align": "center"})
                with solara.Row(style={"width": "100%", "min-width": "20rem", "justify-content": "center", "background-color": "transparent"}):
                    Algolia()
            with solara.Row(gap="20px", classes=["docs-card-container"]):
                for route in route_current.children:
                    if route.path in ["/", "advanced", "faq"]:
                        continue
                    with solara.Link("/documentation/" + route.path):
                        with solara.Row(
                            classes=["docs-card"],
                            style={
                                "background-color": f"var({'--docs-color-grey' if route.path != 'getting_started' else '--color-primary'})",
                            },
                        ):
                            with solara.Column(style={"height": "100%", "flex-grow": "1", "background-color": "transparent"}):
                                solara.HTML(tag="h2", unsafe_innerHTML=route.label, style={"color": "white", "padding": "1.5rem"})
                            with solara.Column(style={"justify-content": "center", "height": "100%", "background-color": "transparent"}):
                                solara.v.Icon(children=["mdi-arrow-right"], color="var(--color-grey-light)", x_large=True, class_="docs-card-icon")
            with solara.Row(gap="75px", style={"flex-wrap": "wrap", "row-gap": "75px", "padding-bottom": "75px"}):
                with solara.Column(style={"padding-left": "10%"}):
                    solara.HTML(tag="h2", unsafe_innerHTML="How to use our documentation:", style={"padding": "1.5rem"})
                    solara.Markdown(
                        """
* [Getting Started](/documentation/getting_started) - Learn how to install Solara and get started with building your app.
    Also includes tutorials for you to get a hang of Solara workflow.
* [Examples](/documentation/examples) - More complex and real world applicable examples of Solara apps.
    For even more complexity you can see the [Showcase](/showcase) page.
* [Components](/documentation/components) - All the components that are available in Solara.
* [API](/documentation/api) - All the API functions that are available in Solara. Importantly, this includes routing and hooks.
* [Advanced](/documentation/advanced) - Advanced topics like associated and underlying libraries.
    If a component you would like to use is not available in Solara, you can use the underlying library directly.
                    """
                    )
                with solara.Column(style={"justify-content": "center", "height": "100%"}):
                    solara.HTML(tag="h2", unsafe_innerHTML="Also Check Out", style={"padding": "1.5rem"})
                    with solara.Row(gap="20px", style={"flex-wrap": "wrap", "row-gap": "20px", "align-items": "center"}):
                        with solara.v.Html(tag="a", attributes={"href": "https://discord.solara.dev", "target": "_blank"}):
                            with solara.Div(classes=["social-logo-container"], style={"background-color": "var(--docs-social-discord)"}):
                                solara.v.Html(tag="img", attributes={"src": "/static/public/social/discord.svg"}, style_="height: 1.5rem; width: auto;")
                        solara.Text("We use discord to provide support and answer questions there actively.")
                    with solara.Row(gap="20px", style={"flex-wrap": "wrap", "row-gap": "20px", "align-items": "center"}):
                        with solara.v.Html(tag="a", attributes={"href": "https://github.com/widgetti/solara", "target": "_blank"}):
                            with solara.Div(classes=["social-logo-container"], style={"background-color": "var(--docs-social-github)"}):
                                solara.v.Html(tag="img", attributes={"src": "/static/public/social/github.svg"}, style_="height: 1.5rem; width: auto;")
                        solara.Text("Search for solutions on Github issues, or report bugs.")
                    with solara.Row(gap="20px", style={"flex-wrap": "wrap", "row-gap": "20px", "align-items": "center"}):
                        with solara.v.Html(tag="a", attributes={"href": "https://twitter.com/solara_dev", "target": "_blank"}):
                            with solara.Div(classes=["social-logo-container"], style={"background-color": "var(--docs-social-twitter)"}):
                                solara.v.Html(tag="img", attributes={"src": "/static/public/social/twitter.svg"}, style_="height: 1.5rem; width: auto;")
                        solara.Text("Get announcements about Solara features, showcases, and events!.")

        else:
            with solara.Column(align="center", children=children, style={"padding": "0"}):
                pass


@solara.component
def Layout(children=[]):
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")

    if route_current.path == "/":
        return Page()
    else:
        return Page(children=children)


@solara.component
def Overview():
    pass
