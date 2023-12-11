"""# Task

"""
import solara
import solara.autorouting
import solara.lab
from solara.website.utils import apidoc

from . import NoPage

title = "Task"
Page = NoPage
__doc__ += apidoc(solara.lab.task)  # type: ignore
