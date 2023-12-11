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

    img = "https://dxhl76zpt6fap.cloudfront.net/public/docs/tutorial/jupyter-dashboard1.webp"
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

    Notebook(
        Path(HERE / "_jupyter_dashboard_1.ipynb"),
        show_last_expressions=True,
        execute=False,
        outputs={
            "a7d17a84": None,  # empty output (7)
            # original: https://github.com/widgetti/solara/assets/1765949/e844acdb-c77d-4df4-ba4c-a629f92f18a3
            "82f1d2f7": solara.Image("https://dxhl76zpt6fap.cloudfront.net/pages/docs/content/60-jupyter-dashboard-part1/map.webp"),  # map (11)
            "3e7ea361": None,  # (13)
            # original: https://github.com/widgetti/solara/assets/1765949/daaa3a46-61f5-431f-8003-b42b5915da4b
            "56055643": solara.Image("https://dxhl76zpt6fap.cloudfront.net/pages/docs/content/60-jupyter-dashboard-part1/view.webp"),  # View (15)
            # original: https://github.com/widgetti/solara/assets/1765949/2f4daf0f-b7d8-4f70-b04a-c27542cffdb0
            "c78010ec": solara.Image("https://dxhl76zpt6fap.cloudfront.net/pages/docs/content/60-jupyter-dashboard-part1/page.webp"),  # Page (20)
            # original: https://github.com/widgetti/solara/assets/1765949/a691d9f1-f07b-4e06-b21b-20980476ad64
            "18290364": solara.Image("https://dxhl76zpt6fap.cloudfront.net/pages/docs/content/60-jupyter-dashboard-part1/controls.webp"),  # Controls
            "0ca68fe8": None,
            "fef5d187": None,
            # original: https://github.com/widgetti/solara/assets/1765949/f0075ad1-808d-458c-8797-e460ce4dc06d
            "af686391": solara.Image("https://dxhl76zpt6fap.cloudfront.net/pages/docs/content/60-jupyter-dashboard-part1/full-app.webp"),  # Full app
        },
    )
    solara.Markdown(
        """
        Explore this app live at [solara.dev](/apps/jupyter-dashboard-1).

        Don’t miss the next tutorial and stay updated with the latest techniques and insights by subscribing to our newsletter.
    """
    )
    location = solara.use_router().path
    MailChimp(location=location)
