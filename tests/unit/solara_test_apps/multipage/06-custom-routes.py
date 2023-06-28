import solara


@solara.component
def Page1():
    solara.Button("hi1")


@solara.component
def Page2():
    solara.Button("hi2")


routes = [
    solara.Route(path="/", component=Page1, label="Hi1"),
    solara.Route(path="page2", component=Page2, label="Hi2"),
]
