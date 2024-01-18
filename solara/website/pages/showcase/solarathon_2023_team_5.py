import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column(align="end", style={"height": "100%", "justify-content": "center"}):
            solara.Markdown(
                """
                    Team 5 built a tool for analyzing sports videos, which allows users to select or upload a video, and then analyse it using
                    point tracking, and object recognition. Because of the nature of the project, adding further analysis tools is very easy.

                    Note: The dashboard is no longer live on Ploomber, but you can see a preview of it in the video, or run it through
                    [GitHub](https://github.com/FelipeCabelloE/solarathon-team5/), using CodeSpaces.
                """
            )
        with solara.v.Html(tag="video", attributes={"controls": "controls", "autoplay": "autoplay"}, style_="width:100%;"):
            solara.v.Html(
                tag="source",
                attributes={"src": "https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_5/preview.webm", "type": "video/webm"},
            )
