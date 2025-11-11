"""# Task"""

import solara
import solara.autorouting
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "Task"
Page = NoPage
__doc__ += apidoc(solara.task)  # type: ignore
