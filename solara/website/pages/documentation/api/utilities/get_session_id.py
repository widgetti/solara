"""
# get_session_id

"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "get_session_id"


Page = NoPage


__doc__ += apidoc(solara.get_session_id)  # type: ignore
