"""
# FigureBokeh

Display a Bokeh figure.

"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "FigureBokeh"

__doc__ += apidoc(solara.lab.components.figurebokeh.FigureBokeh.f)  # type: ignore

Page = NoPage
