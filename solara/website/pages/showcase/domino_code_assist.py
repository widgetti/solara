import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        solara.Markdown(
            """
        # Domino code assist

        [Domino Code Assist](https://www.dominodatalab.com/product/code-assist) (DCA) is a tool developed for [Domino Data Lab](https://www.dominodatalab.com/)
        which provides a simple, intuitive point-and-click interface for generating Python or R code.
        DCA uses many of the solara components to render the UI in the classical notebook and lab. Solara server is used to serve data apps.

        Domino code assist is deeply integrated in the Jupyter notebook.
        """
        )
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/lca/load-data-lab.png", width="100%", classes=["pt-12"])

    with solara.ColumnsResponsive(12, medium=6):
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/lca/viz.png", width="100%", classes=["pt-12"])
        solara.Markdown(
            """
        # Sophisticated UIs

        Using Solara, we can build sophisticated UIs that are easy to use, intuitive
        and have a modern look and feel.

        """
        )

    with solara.ColumnsResponsive(12, medium=6):
        solara.Markdown(
            """
        # Making apps.

        Using Solara we could build an "What You See Is What You Get" app designer.
        All solara components look and feel the same in the notebook and in the deployed app.

        """
        )
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/lca/app-design.png", width="100%", classes=["pt-12"])

    with solara.ColumnsResponsive(12, medium=6):
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/lca/app-deployed.png", width="100%", classes=["pt-12"])
        solara.Markdown(
            """

            # App deploying

            To deploy apps we use [solara server](/docs/understanding/solara-server) which can
            render the same UI as in the notebook, but now sharable with non-technical users.

            Many users have deployed apps at Domino using Solara with
            a single click.

            """
        )
