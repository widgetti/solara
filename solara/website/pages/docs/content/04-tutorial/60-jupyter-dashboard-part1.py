from pathlib import Path

import solara
from solara.website.components.mailchimp import MailChimp
from solara.website.components.notebook import Notebook

HERE = Path(__file__).parent
title = "Jupyter Dashboard (1/3)"


@solara.component
def Page():
    title = "Build your Jupyter dashboard using Solara"
    solara.Meta(property="og:title", content=title)
    solara.Meta(name="twitter:title", content=title)
    solara.Title(title)

    img = "https://solara.dev/static/public/docs/tutorial/jupyter-dashboard1.jpg"
    solara.Meta(name="twitter:image", content=img)
    solara.Meta(property="og:image", content=img)

    description = "Learn how to build a Jupyter dashboard and deploy it as a web app using Solara."
    solara.Meta(name="description", property="og:description", content=description)
    solara.Meta(name="twitter:description", content=description)
    tags = [
        "jupyter",
        "jupyter dashboard",
        "dashboard",
        "web app",
        "deploy",
        "solara",
    ]
    solara.Meta(name="keywords", content=", ".join(tags))

    Notebook(Path(HERE / "_jupyter_dashboard_1.ipynb"), show_last_expressions=True)
    solara.Markdown(
        """
        Don’t miss the next tutorial and stay updated with the latest techniques and insights by subscribing to our newsletter.
    """
    )
    location = solara.use_router().path
    MailChimp(location=location)
