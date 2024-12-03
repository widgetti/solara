import solara
from solara.website.components.contact import Contact


@solara.component
def Page():
    with solara.Column(gap="40px", align="stretch", style={"width": "100%", "padding-bottom": "140px"}):
        with solara.Div(style={"display": "none"}):
            title = "Scaling up your ipywidgets apps"
            solara.Meta(property="og:title", content=title)
            solara.Meta(name="twitter:title", content=title)
            solara.Title(title)

            description = "Learn how to transform your ipywidget app or prototype into a production ready high quality app."
            solara.Meta(name="description", property="og:description", content=description)
            solara.Meta(name="twitter:description", content=description)

        solara.Markdown("""
# Scaling up your ipywidgets app

## The problem
We at Widgetti, the creators of Solara, have regularly seen companies struggle trying to scale up their ipywidgets apps.

These app often start as a prototype or a small app in the Jupyter notebook, and become important internal apps. Together with Voila
it allows companies to quickly deploy an app internally. However, as the app grows, the complexity of the app grows as well and the app
becomes harder to maintain and scale, and extend and testing is often an afterthought.

## Our solution
If you are in this position, you are not alone. We have seen this happen many times and we have helped many companies to scale up their ipywidgets apps.
This can go from small improvements to the app, to a complete rewrite of the app. We often recomment an incremental approach, where we make sure the app
gets tested properly, and gradually introduce best practices to the app and your team as well as introducing modern state management techniques.

We continuously do code review and assist your team in making the app more maintainable and scalable. We can also help with the deployment of the app.

Over time, we phase out our involvement and make sure your team is able to maintain and extend the app themselves. We can also provide training and workshops
if needed.

Please contact us below for a free consultation where we can discuss your needs and how we can help you, or send us an email at [contact@solara.dev](mailto:contact@solara.dev).

                        """)
        Contact(
            title="Get In Touch",
            subtitle="Please fill out the form below and we will get back to you as soon as possible.",
            email_subject="Scaling up your ipywidgets app",
        )
