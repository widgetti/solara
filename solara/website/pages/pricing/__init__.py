import solara
from solara.website.components.contact import Contact


@solara.component
def Page():
    with solara.Column(gap="40px", align="stretch", style={"width": "100%"}):
        solara.Markdown("""
# Pricing

The main Solara package is free for both personal and commercial use. There are additional components and functionality available in the `solara-enterprise` package, which is free for personal use, but requires a license for commercial use.
        """)
        solara.Markdown("""
## Enterprise License

As stated before, the `solara-enterprise` package is free for personal use, but requires a license for commercial use. The license includes the following benefits:

- Access to all `solara-enterprise` components and functionality
- Priority support from the Solara team, including bug fixes and questions
- Potential for custom components and functionality as agreed separately
- Trainings and workshops for your team
- Regular code reviews and/or design consultation

All enterprise licenses are custom and are priced based on the needs of the organization. Please contact us below for more information.
        """)

        Contact(
            title="Get In Touch",
            subtitle="Please fill out the form below and we will get back to you as soon as possible.",
            email_subject="Enterprise License Inquiry",
        )
