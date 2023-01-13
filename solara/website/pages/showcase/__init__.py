import solara

title = "Showcase"


@solara.component
def Page():
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Card("solara.dev", style={"height": "100%"}):
            solara.Markdown(
                """
            The Solara.dev website is built using Solara itself, showcasing the library's features and capabilities.
            All documentation and example are on this page.
            """
            )
            with solara.Link("./solara_dev"):
                solara.Image("/static/public/showcase/solara/thumbnail.png", width="100%")
        with solara.Card("Domino Code Assist", style={"height": "100%"}):
            solara.Markdown(
                """
            Domino Code Assist (DCA) is a tool developed for Domino Data Lab which provides a simple, intuitive point-and-click interface for generating
            Python or R code.
            """
            )
            with solara.Link("./domino_code_assist"):
                solara.Image("/static/public/showcase/lca/thumbnail.png", width="100%")

        with solara.Card("TESSA", style={"height": "100%"}):
            solara.Markdown(
                """
            [TESSA](https://planeto-energy.ch/solution/) is a tool developed by Planeto for district heating & cooling planning.
            """
            )
            with solara.Link("./planeto_tessa"):
                solara.Image("/static/public/showcase/tessa/thumbnail.png", width="100%")
