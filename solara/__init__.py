"""Build webapps using IPywidgets"""
__version__ = "0.9.1"
github_url = "https://github.com/widgetti/solara"
git_branch = "master"
# isort: skip_file

from . import util

# flake8: noqa: F402
from .datatypes import *
from .hooks import *
from .memoize import memoize
from .components import *

from .routing import use_route, use_router, use_route_level, find_route, use_pathname, resolve_path
from .autorouting import generate_routes, generate_routes_directory, RenderPage, RoutingProvider, DefaultLayout
