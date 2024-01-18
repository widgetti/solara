import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column(align="end", style={"height": "100%", "justify-content": "center"}):
            solara.Markdown(
                """
                Team 2 built a travel assistant, which utilized various third party APIs to display rich information about the desired destination
                during the dates selected for a visit. The assistant also provided a list of recommended activities, and a map of the area.

                Take a look at the project on [Ploomber](https://jolly-moon-5966.ploomberapp.io/)
                """
            )
        with solara.v.Html(tag="video", attributes={"controls": "controls", "autoplay": "autoplay"}, style_="width:100%;"):
            solara.v.Html(
                tag="source",
                attributes={"src": "https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_2/preview.webm", "type": "video/webm"},
            )
