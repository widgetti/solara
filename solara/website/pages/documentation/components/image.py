"""# Image

"""
import solara
from solara.website.utils import apidoc

from . import NoPage

Page = NoPage
title = "Image"


__doc__ += apidoc(solara.Image.f)  # type: ignore
