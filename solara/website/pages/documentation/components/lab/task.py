"""# Task"""

import solara
import solara.autorouting
import solara.lab
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "Task"
Page = NoPage
__doc__ += apidoc(solara.lab.task)  # type: ignore
