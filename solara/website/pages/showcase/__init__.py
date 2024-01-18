import solara

title = "Showcase"


@solara.component
def Page():
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Card("Wanderlust", style={"height": "100%"}):
            solara.Markdown(
                """
            [Wanderlust](./wanderlust) is a reproduction of the travel assistant demo shown at the
            [OpenAI DevDay](https://devday.openai.com/) 2023, built using Solara and the OpenAI Assistants API.
            """
            )
            with solara.Link("./wanderlust"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/wanderlust/thumbnail.png", width="100%")
            with solara.v.Html(tag="a", attributes={"href": "https://github.com/widgetti/wanderlust", "target": "_blank"}):
                with solara.Row(style={"min-height": "24px"}):
                    solara.v.Icon(children=["mdi-github-circle"], x_large=True, class_="mr-2")

        with solara.Card("Domino Code Assist", style={"height": "100%"}):
            solara.Markdown(
                """
            Domino Code Assist (DCA) is a tool developed for Domino Data Lab which provides a simple, intuitive point-and-click interface for generating
            Python or R code.
            """
            )
            with solara.Link("./domino_code_assist"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/lca/thumbnail.png", width="100%")

        with solara.Card("TESSA", style={"height": "100%"}):
            solara.Markdown(
                """
            [TESSA](https://planeto-energy.ch/solution/) is a tool developed by Planeto for district heating & cooling planning.
            """
            )
            with solara.Link("./planeto_tessa"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/tessa/thumbnail.png", width="100%")

        with solara.Card("Bulk labeling", style={"height": "100%"}):
            solara.Markdown(
                """
            [Bulk labeling](https://github.com/Ben-Epstein/solara-examples/tree/main/bulk-labeling)
            is a tool developed by Ben Epstein for labeling data in bulk."""
            )
            from solara.alias import rv

            img = "https://avatars.githubusercontent.com/u/22605641?v=4"
            with rv.Html(tag="a", attributes={"href": "https://github.com/Ben-Epstein/solara-examples/tree/main/bulk-labeling", "target": "_blank"}):
                solara.Image("https://user-images.githubusercontent.com/1765949/237517090-8f7242b1-3189-4c5b-abd3-0f0986292ade.png", width="100%")
            with rv.Html(tag="a", attributes={"href": "https://github.com/Ben-Epstein/", "target": "_blank"}):
                with rv.ListItem(class_="grow"):
                    with rv.ListItemAvatar(color="grey darken-3"):
                        rv.Img(
                            class_="elevation-6",
                            src=img,
                        )

        with solara.Card("solara.dev", style={"height": "100%"}):
            solara.Markdown(
                """
            The Solara.dev website is built using Solara itself, showcasing the library's features and capabilities.
            All documentation and example are on this page.
            """
            )
            with solara.Link("./solara_dev"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solara/thumbnail.png", width="100%")

    solara.HTML(tag="h1", unsafe_innerHTML="Solarathon 2023")
    solara.Markdown(
        """
                    In November 2023, we hosted the first Solarathon, a two-week hackathon,
                    during which participants built projects using Solara, and deployed them to [Ploomber](https://ploomber.io/).
                    The event was a great success, and we are looking forward to hosting more Solarathons in the future.
                    The projects built during the event are showcased below."""
    )
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Card("Team 2: Travel Assistant", style={"height": "100%"}):
            with solara.Link("./solarathon_2023_team_2"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_2/thumbnail.png", width="100%")
            with solara.v.Html(tag="a", attributes={"href": "https://github.com/alonsosilvaallende/solarathon", "target": "_blank"}):
                with solara.Row(style={"min-height": "24px"}):
                    solara.v.Icon(children=["mdi-github-circle"], x_large=True, class_="mr-2")

        with solara.Card("Team 4: Live Cryptocurrency Dashboard", style={"height": "100%"}):
            with solara.Link("./solarathon_2023_team_4"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_4/thumbnail.png", width="100%")
            with solara.v.Html(tag="a", attributes={"href": "https://github.com/theeldermillenial/solarathon", "target": "_blank"}):
                with solara.Row(style={"min-height": "24px"}):
                    solara.v.Icon(children=["mdi-github-circle"], x_large=True, class_="mr-2")

        with solara.Card("Team 5: Sports Video Analysis", style={"height": "100%"}):
            with solara.Link("./solarathon_2023_team_5"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_5/thumbnail.png", width="100%")
            with solara.v.Html(tag="a", attributes={"href": "https://github.com/FelipeCabelloE/solarathon-team5/", "target": "_blank"}):
                with solara.Row(style={"min-height": "24px"}):
                    solara.v.Icon(children=["mdi-github-circle"], x_large=True, class_="mr-2")

        with solara.Card("Team 6: Automatic FAQ Creator", style={"height": "100%"}):
            with solara.Link("./solarathon_2023_team_6"):
                solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_6/thumbnail.png", width="100%")
            with solara.v.Html(tag="a", attributes={"href": "https://github.com/silvhua/solarathon-faq-creator", "target": "_blank"}):
                with solara.Row(style={"min-height": "24px"}):
                    solara.v.Icon(children=["mdi-github-circle"], x_large=True, class_="mr-2")
