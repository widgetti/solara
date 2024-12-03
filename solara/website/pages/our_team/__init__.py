import solara


@solara.component
def Page():
    with solara.Column(gap="40px", style={"max-width": "90%"}):
        solara.Markdown("""
# Our Team

Solara is primarily developed by [Widgetti](https://widgetti.io/), a software development company specializing in the front-end side of the jupyter ecosystem. Widgetti was founded by Maarten Breddels and Mario Buikhuizen in 2023, and is based in the Netherlands.

## Core Team
        """)
        DevCard(
            "Maarten Breddels",
            "Co-Founder of Widgetti, Creator of Solara",
            "https://github.com/maartenbreddels",
            "Maarten is the creator of Solara, ipyvolume, and a founder of Widgetti. He is a core developer of the [Vaex](https://vaex.io/) project, and has a background in working with large datasets in astronomy.",
            image="https://dxhl76zpt6fap.cloudfront.net/public/avatar/maarten-breddels.jpeg",
            linkedin="https://www.linkedin.com/in/maartenbreddels/",
            twitter="https://twitter.com/maartenbreddels",
            email="maartenbreddels@widgetti.io",
        )
        DevCard(
            "Mario Buikhuizen",
            "Co-Founder of Widgetti",
            "https://github.com/mariobuikhuizen",
            "Mario is a co-founder of Widgetti and has a background in software development and data engineering. He is the creator of [ipyvuetify](https://github.com/widgetti/ipyvuetify) and [ipyvue](https://github.com/widgetti/ipyvue).",
            image="https://dxhl76zpt6fap.cloudfront.net/public/avatar/mario-buikhuizen.jpeg",
            linkedin="https://www.linkedin.com/in/mariobuikhuizen/",
            twitter="https://twitter.com/mariobuikhuizen",
            email="mariobuikhuizen@widgetti.io",
        )
        DevCard(
            "Iisakki Rotko",
            "Medior Software Engineer",
            "https://github.com/iisakkirotko",
            "Iisakki is a medior software engineer at Widgetti, working primarily on Solara. He has a background in physics and web development.",
            image="https://dxhl76zpt6fap.cloudfront.net/public/avatar/iisakki-rotko.jpg",
            linkedin="https://www.linkedin.com/in/iisakkirotko/",
            email="iisakki.rotko@widgetti.io",
        )


@solara.component
def DevCard(
    name,
    role,
    github,
    bio,
    image=None,
    linkedin=None,
    twitter=None,
    website=None,
    email=None,
):
    with solara.Row(gap="40px", style={"align-items": "stretch", "max-height": "300px", "flex": "1 1 auto"}):
        with solara.Div(style={"flex": "0 1 300px", "border-radius": "15px", "overflow": "hidden", "aspect-ratio": "1/1"}):
            solara.v.Html(
                tag="img",
                attributes={"src": image or "https://dxhl76zpt6fap.cloudfront.net/public/logo.svg", "alt": name},
                style_="height: 100%; aspect-ratio: 1; object-fit: cover;",
            )
        with solara.Column():
            solara.HTML(tag="h2", unsafe_innerHTML=name)
            solara.HTML(tag="h3", unsafe_innerHTML=role)
            solara.Markdown(bio)
            with solara.Row(gap="10px"):
                if linkedin:
                    with solara.v.Html(tag="a", attributes={"href": linkedin, "target": "_blank"}):
                        solara.v.Icon(children=["mdi-linkedin"], color="var(--color-grey-light)")
                if twitter:
                    with solara.v.Html(tag="a", attributes={"href": twitter, "target": "_blank"}):
                        solara.v.Icon(children=["mdi-twitter"], color="var(--color-grey-light)")
                if website:
                    with solara.v.Html(tag="a", attributes={"href": website, "target": "_blank"}):
                        solara.v.Icon(children=["mdi-web"], color="var(--color-grey-light)")
                if email:
                    with solara.v.Html(tag="a", attributes={"href": f"mailto:{email}"}):
                        solara.v.Icon(children=["mdi-email"], color="var(--color-grey-light)")
                if github:
                    with solara.v.Html(tag="a", attributes={"href": github, "target": "_blank"}):
                        solara.v.Icon(children=["mdi-github"], color="var(--color-grey-light)")
