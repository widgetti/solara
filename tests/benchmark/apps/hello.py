# Smallest app: one Text and the default layout (AppLayout).
# On master, Text is an ipyvuetify.Html, so this needs Vuetify until Text renders as ipyvue.Html.
import solara


@solara.component
def Page():
    solara.Text("Hello benchmark")
