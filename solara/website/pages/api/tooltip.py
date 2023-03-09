"""# Tooltip

"""
import solara
from solara.website.utils import apidoc

from . import NoPage

Page = NoPage
title = "Tooltip"


__doc__ += apidoc(solara.Tooltip.f)  # type: ignore
