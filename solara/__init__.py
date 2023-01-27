"""Build webapps using IPywidgets"""
__version__ = "1.2.1"
github_url = "https://github.com/widgetti/solara"
git_branch = "master"


def _using_solara_server():
    import sys

    return "solara.server" in sys.modules


# isort: skip_file
from reacton import (
    component,
    component_interactive,
    value_component,
    create_context,
    display,
    get_widget,
    make,
    provide_context,
    render,
    render_fixed,
    use_context,
    use_effect,
    use_exception,
    use_memo,
    use_reducer,
    use_ref,
    use_side_effect,
    use_state,
    use_state_widget,
)  # noqa: F403, F401
from . import util

# flake8: noqa: F402
from .datatypes import *
from .hooks import *
from .cache import memoize
from . import cache
from .components import *

from .routing import use_route, use_router, use_route_level, find_route, use_pathname, resolve_path
from .autorouting import generate_routes, generate_routes_directory, RenderPage, RoutingProvider, DefaultLayout
