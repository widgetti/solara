"""# use_task"""

import solara
import solara.autorouting
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "use_task"
Page = NoPage
__doc__ += apidoc(solara.use_task)  # type: ignore
