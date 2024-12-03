import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column(align="end", style={"height": "100%", "justify-content": "center"}):
            solara.Markdown(
                """
                    Team 4 built a live cryptocurrency dashboard, which displayed the latest prices for various cryptocurrencies, and versatile
                    analysis tools to help users make informed decisions.

                    Note: The dashboard is no longer live on Ploomber, but you can see a preview of it in the video, or run it by cloning the GitHub repository.
                """
            )
        with solara.v.Html(tag="video", attributes={"controls": "controls", "autoplay": "autoplay"}, style_="width:100%;"):
            solara.v.Html(
                tag="source",
                attributes={"src": "https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_4/preview.webm", "type": "video/webm"},
            )
