import solara
from solara.website.components import NoPage, SubCategoryLayout

Page = NoPage


@solara.component
def Layout(children=[]):
    SubCategoryLayout(children=children)
