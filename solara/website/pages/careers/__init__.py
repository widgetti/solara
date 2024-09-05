import solara


@solara.component
def Page():
    with solara.Column():
        solara.Markdown(
            """
            # Careers
            We are always looking for talented individuals to join our team. If you're still be interested after reading the rest of this page, reach out at [contact@widgetti.io](mailto:contact@widgetti.io).
            """
        )
        with solara.Row(style={"flex-wrap": "wrap", "align-items": "stretch"}, gap="0"):
            with Tile():
                solara.Markdown(
                    """
                    ## Who Are We?
                    We are a small team of developers working in the gap between Jupyter notebooks and web applications. We are passionate about making data science more accessible and app development painless.
                    We are based in Groningen, The Netherlands, but work remote first.
                    """
                )
            with Tile(background_color="var(--dark-color-primary-lightest)"):
                solara.Markdown(
                    """
                    ## What Do We Offer?
                    We offer a flexible work environment, competitive salary, and the opportunity to do meaningful, crossdisciplinary work with scientists and companies worldwide.
                    We are a small team, so you will have a lot of freedom in your work, and the chance to get your hands dirty with many projects.
                    """
                )
            with Tile(background_color="rgb(255, 233, 31)"):
                solara.Markdown(
                    """
                    ## Who Are We Looking For?
                    We are looking for developers, technical writers, designers, and everything in between.
                    """,
                    style={"--dark-color-text": "black", "--color-text": "black", "color": "black"},
                )


@solara.component
def Tile(children=[], background_color="var(--dark-color-primary)", color="white"):
    with solara.Div(children=children, style={"flex": "1 1 0", "min-width": "250px", "padding": "30px", "background-color": background_color, "color": color}):
        pass
