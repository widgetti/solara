import solara
from solara.alias import rv


@solara.component
def Hero(title, sub_title, button_text):
    with rv.Html(tag="section", class_="hero text-center") as main:
        with rv.Container():
            with rv.Row():
                with rv.Col(md=8, offset_md=2, sm=10, offset_sm=1):
                    rv.Html(tag="h1", children=[title], class_="mb-4"),
                    solara.HTML(tag="div", unsafe_innerHTML=f"<h2>{sub_title}</h2>", class_="mb-4"),
                    with solara.Link("/docs/quickstart"):
                        solara.Button(label=button_text, elevation=0, large=True, class_="btn-size--xlarge solara-docs-button")
    return main
