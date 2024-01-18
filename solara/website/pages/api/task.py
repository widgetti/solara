"""# Task

A global way to run code in the background, with the UI available to the user. This is useful for long running tasks, like downloading data.

"""
import solara
import solara.autorouting
import solara.lab
from solara.website.utils import apidoc

from . import NoPage

title = "task"
Page = NoPage
__doc__ += apidoc(solara.lab.task)  # type: ignore
