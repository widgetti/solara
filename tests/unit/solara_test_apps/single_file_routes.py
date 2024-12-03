import solara


@solara.component
def Page1():
    solara.Text("Page 1")


@solara.component
def Page2():
    solara.Text("Page 2")


@solara.component
def Layout(children):
    with solara.AppLayout():
        with solara.Column():
            solara.Text("Custom layout")
            solara.display(*children)


routes = [
    solara.Route("/", component=Page1, layout=Layout),
    solara.Route("page2", component=Page2),
]
