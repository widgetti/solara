import solara


@solara.component
def Page():
    with solara.Link("/showcase"):
        solara.Text("« Back to Showcases")
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column(align="end", style={"height": "100%", "justify-content": "center"}):
            solara.Markdown(
                """
                [Wanderlust](https://huggingface.co/spaces/solara-dev/wanderlust) is a reproduction of the travel assistant demo shown at the
                [OpenAI DevDay](https://devday.openai.com/) 2023, built using Solara and the OpenAI Assistants API.

                The sourcecode of the demo is available on [github](https://github.com/widgetti/wanderlust)
                """
            )
        with solara.v.Html(tag="a", style_="width: 100%;", attributes={"href": "https://huggingface.co/spaces/solara-dev/wanderlust", "target": "_blank"}):
            solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/wanderlust/thumbnail.png", width="100%")
    with solara.ColumnsResponsive(12, medium=6):
        with solara.v.Html(tag="a", style_="width: 100%;", attributes={"href": "https://huggingface.co/spaces/solara-dev/wanderlust", "target": "_blank"}):
            solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/showcase/wanderlust/assistant.png", width="100%")
        with solara.Column(align="end", style={"height": "100%", "justify-content": "center"}):
            solara.Markdown(
                """Using the new [function calling feature](https://platform.openai.com/docs/guides/function-calling) of OpenAI Assistants, the
                            assistant can annotate, move, and zoom the map to provide additional functionality"""
            )
