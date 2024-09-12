import solara


@solara.component
def Page():
    with solara.Column():
        solara.Markdown(
            """
            # Careers
            We are always looking for talented individuals to join our team. If you're still be interested after reading the rest of this page, reach out at [contact@widgetti.io](mailto:contact@widgetti.io).

            ## Who Are We?
            We are a small team of developers working in the gap between Jupyter notebooks and web applications. We are passionate about making data science more accessible and app development painless.
            We are based in Groningen, The Netherlands, but work remote first.

            ## What Do We Offer?
            We offer a flexible work environment, competitive salary, and the opportunity to do meaningful, crossdisciplinary work with scientists and companies worldwide.
            We are a small team, so you will have a lot of freedom in your work, and the chance to get your hands dirty with many projects.

            ### Open Source
            We are strong believers in open source software. When working with us, you can expect the majority of the software you write to be open source, with contributions to Solara as well as other open source projects.

            ## Who Are We Looking For?
            We are looking for developers, technical writers, designers, and everything in between.
            """,
            style={"max-width": "90%", "margin": "0 auto"},
        )
