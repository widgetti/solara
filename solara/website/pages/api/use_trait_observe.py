"""# use_trait_observe

"""
import solara
import solara.autorouting
import solara.lab
from solara.website.utils import apidoc

from . import NoPage

title = "use_trait_observe"
Page = NoPage
__doc__ += apidoc(solara.use_trait_observe)  # type: ignore
