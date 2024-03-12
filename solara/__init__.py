"""Build webapps using IPywidgets"""
__version__ = "1.29.1"
github_url = "https://github.com/widgetti/solara"
git_branch = "master"


from . import comm  # noqa: F401


def _using_solara_server():
    import sys

    if "solara.server" in sys.modules:
        return True
    if sys.argv[0].split("/")[-1] == "solara":
        return True
    return False


# isort: skip_file
from reacton import (
    component,
    component_interactive,
    value_component,
    create_context,
    get_widget,
    get_context,
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
from reacton.core import Element  # noqa: F403, F401

try:
    import ipyvuetify.components as v  # type: ignore # noqa: F401
except ModuleNotFoundError:
    # backwards compatibility
    import reacton.ipyvuetify as v  # type: ignore # noqa: F401
from . import util

from .reactive import *

# flake8: noqa: F402
from .datatypes import *
from .hooks import *
from .cache import memoize
from . import cache

# TODO: components re-exports v, we should use __all__ in components/misc.py
from .components import *  # type: ignore
from .components import _component_vue

from .routing import use_route, use_router, use_route_level, find_route, use_pathname, resolve_path
from .autorouting import generate_routes, generate_routes_directory, RenderPage, RoutingProvider, DefaultLayout
from .checks import check_jupyter
from .scope import get_kernel_id, get_session_id


def display(*objs, **kwargs):
    """Display a Python object in the current component.

    ## Supported objects

    Any object that can be displayed in the Jupyter notebook can be displayed in Solara
    as well. This means that plotly, pandas, vaex and other libraries that have
    a display function will work out of the box in Solara.

    However, if you require callback functions, use the specific Solara components, e.g.:

      * [Plotly](/api/plotly)
      * [Altair](/api/altair)
      * [Matplotlib](/api/matplotlib)
      * [Dataframe](/api/dataframe)

    ```solara
    import solara
    import pandas as pd
    import plotly.express as px

    df = px.data.gapminder()
    fig = px.scatter(df, x="gdpPercap", y="lifeExp")
    button = solara.Button("Click me")

    @solara.component
    def Page():

        # You can use solara.display directly
        solara.display(fig)

        # Or use the IPython display function, which is in the global scope
        # in Jupyter and Solara
        display(df)

        with solara.Card("Some card"):
            # you can use display to add existing elements to the parent's
            # children
            display(button)
    ```
    Note that this is a dispatch call to the
    [IPython display function](https://ipython.readthedocs.io/en/stable/api/generated/IPython.display.html#IPython.display.display),
    with a slimmer API. The main purpose of this function is the have type safety, since tools like mypy do now know about
    the existence of the IPython display function, and will complain if you use it without importing it.
    Since solara is always imported, this saves you from having to import IPython in your code.

    ## Arguments

     * `objs`: The objects to display.
     * `kwargs`: Keyword arguments to pass to the IPython display function.

    """
    from IPython.display import display as ipy_display

    ipy_display(*objs, **kwargs)
