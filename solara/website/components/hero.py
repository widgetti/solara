from solara.alias import react, rv, sol


@react.component
def Hero(title, button_text):
    with rv.Html(tag="section", class_="hero text-center") as main:
        with rv.Container():
            with rv.Row():
                with rv.Col(md=8, offset_md=2, sm=10, offset_sm=1):
                    rv.Html(tag="h1", children=[title], class_="mb-4"),
                    with sol.Link("/docs/quickstart"):
                        sol.Button(label=button_text, elevation=0, large=True, class_="btn-size--xlarge")
    return main
