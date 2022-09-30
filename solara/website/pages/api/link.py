"""Create a link to navigate to a route."""


import solara

routes = [
    solara.Route(path="/"),
    solara.Route(path="kiwi"),
    solara.Route(path="banana"),
    solara.Route(path="apple"),
]


@solara.component
def LinkExample():
    route_current, routes = solara.use_route()
    with solara.VBox() as main:
        solara.Info("Note the address bar in the browser. It should change to the path of the link.")
        with solara.HBox():
            for route in routes:
                with solara.Link(route):
                    current = route_current is route
                    solara.Button(f"Go to {route.path}", color="red" if current else None)
    return main


App = LinkExample
app = App()
