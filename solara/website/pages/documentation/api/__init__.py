"""
# Overview
Click on one of the items on the left.
"""

import solara
from solara.website.components import CategoryLayout, Gallery

_title = "API"


@solara.component
def Page(route_external=None):
    Gallery(route_external)


@solara.component
def Layout(children=[]):
    CategoryLayout(children=children)
