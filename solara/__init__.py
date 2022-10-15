"""Build webapps using IPywidgets"""
__version__ = "0.13.0"
github_url = "https://github.com/widgetti/solara"
git_branch = "master"
# isort: skip_file
from reacton import (
    component,
    component_interactive,
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
from .memoize import memoize
from .components import *

from .routing import use_route, use_router, use_route_level, find_route, use_pathname, resolve_path
from .autorouting import generate_routes, generate_routes_directory, RenderPage, RoutingProvider, DefaultLayout
