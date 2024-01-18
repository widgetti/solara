import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column(align="end", style={"height": "100%", "justify-content": "center"}):
            solara.Markdown(
                """
                    Team 6 built an automatic FAQ creator, including a Discord bot, which crawls a Discord server, and creates a FAQ page
                    based on the most frequently asked questions in the server. The Data is then fed through [Haystack](https://haystack.deepset.ai/),
                    which summarizes and categorizes the questions, and provides answers to be displayed on the FAQ page.

                    Take a look at the [GitHub Repository](https://github.com/silvhua/solarathon-faq-creator) for instructions on how to run the project.
                """
            )
        with solara.v.Html(tag="video", attributes={"controls": "controls", "autoplay": "autoplay"}, style_="width:100%;"):
            solara.v.Html(
                tag="source",
                attributes={"src": "https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_6/preview.webm", "type": "video/webm"},
            )

    solara.Markdown(
        """
            ## Project Team Members
            * [Simone Frisco](https://www.linkedin.com/in/simonefrisco/), Data Scientist
            * [Silvia Hua](https://www.linkedin.com/in/silviahua), Data Scientist
            * [Arunprasadh Senthil](https://www.linkedin.com/in/arun-prasadh-senthil/), Data Engineer
            * [Janet Mardjuki](https://www.linkedin.com/in/jmardjuki/), Software Developer
            * [Roman Gampert](https://www.linkedin.com/in/roman-gampert-5537b9126/), Product
        """
    )
