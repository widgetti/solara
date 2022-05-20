"""Build webapps using IPywidgets"""
__version__ = "0.1.0"
# isort: skip_file

from . import util

# flake8: noqa: F402
from .datatypes import *
from .hooks import *
from .memoize import memoize
from .components import *
from .widgets import watch as auto_reload_vue

github_url = "https://github.com/widgetti/solara"
git_branch = "master"
