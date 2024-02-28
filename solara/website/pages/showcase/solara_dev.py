import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        solara.Markdown(
            """
        # Solara.dev

        The Solara.dev website is built using Solara itself, showcasing the library's features and capabilities.
        All documentation and example are on this website.
        """
        )

    with solara.ColumnsResponsive(12, medium=6):
        solara.Markdown(
            """
        ## Desktop and mobile

        Solara.dev is designed to be responsive, working seamlessly on both desktop and mobile devices.
        On smaller screens, the top navigation bar is replaced with a drawer for easy navigation.
        The [`ColumnsResponsive`](/api/columns_responsive) component can be used to create responsive content layouts.

        """
        )
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solara/home-mobile.png", width="100%", classes=["pt-12"])

    with solara.ColumnsResponsive(12, medium=6):
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solara/docs.png", width="100%")
        solara.Markdown(
            """
## Multi-page

The website is composed of multiple pages, illustrating how users can navigate between the home page, documentation, and tutorial sections.

        """
        )

    with solara.ColumnsResponsive(12, medium=6):
        solara.Markdown(
            """
            ## Markdown support

            Solara supports the use of Markdown for creating dynamic and static content.
            This makes it possible to combine Python-generated pages with static Markdown pages in a single website.
            Hot reloading ensures that the page is automatically updated whenever changes are made to the Markdown files.


        """
        )
        solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solara/vscode-markdown.png", width="100%")
