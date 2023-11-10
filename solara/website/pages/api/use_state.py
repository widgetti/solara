"""# use_state

"""
import solara
import solara.autorouting
from solara.website.utils import apidoc

from . import NoPage

title = "use_state"
Page = NoPage
__doc__ += apidoc(solara.use_state)  # type: ignore
