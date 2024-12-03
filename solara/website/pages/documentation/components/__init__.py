import solara
from solara.website.components import CategoryLayout, Gallery


@solara.component
def Page(route_external=None):
    Gallery(route_external)


@solara.component
def Layout(children=[]):
    CategoryLayout(children=children)
