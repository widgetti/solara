"""Create a link to navigate to a route."""


from solara.kitchensink import react, sol

routes = [
    sol.Route(path="/"),
    sol.Route(path="kiwi"),
    sol.Route(path="banana"),
    sol.Route(path="apple"),
]


@react.component
def LinkExample():
    route_current, routes = sol.use_route()
    with sol.VBox() as main:
        sol.Info("Note the address bar in the browser. It should change to the path of the link.")
        with sol.HBox():
            for route in routes:
                with sol.Link(route):
                    current = route_current is route
                    sol.Button(f"Go to {route.path}", color="red" if current else None)
    return main


App = LinkExample
app = App()
