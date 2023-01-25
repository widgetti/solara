import solara


@solara.component
def Page():
    x, set_x = solara.use_state(2)
    x_squared = x**2

    with solara.Sidebar():
        solara.Markdown("## My First Solara app ☀️")
        solara.SliderInt(label="x", value=x, on_value=set_x)
    solara.Markdown(f"{x} squared = {x_squared}")


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    return solara.AppLayout(children=children)
