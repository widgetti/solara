import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        solara.Markdown(
            """
        # TESSA by Planeto

        [Planeto](https://planeto-energy.ch/) developed a tool called [TESSA](https://planeto-energy.ch/solution/) for district heating & cooling planning.

        TESSA was prototyped in the Jupyter notebook using ipywidgets. Using solara, they are able to bring TESSA into production using the
        same technology stack.
        """
        )
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/tessa/thumbnail.png", width="100%", classes=["pt-12"])
