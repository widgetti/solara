import ipyvuetify.Themes
from ipywidgets import Widget
from traitlets import Bool, Unicode

import solara
import solara.server.settings as settings
from solara.server.settings import ThemeVariant
from solara.tasks import Proxy

try:
    # the default ctor gets in the way, we should fix
    # this in ipyvuetify
    del ipyvuetify.Themes.Theme.__init__
except AttributeError:
    pass


# We override ipyvuetify theming
class Theme(Widget):
    """
    A class to override the ipyvuetify theming.
    """

    _model_name = Unicode("ThemeModel").tag(sync=True)

    _model_module = Unicode("jupyter-vuetify").tag(sync=True)

    dark = Bool(settings.theme.variant == ThemeVariant.dark, allow_none=True).tag(sync=True)

    def __init__(self):
        super().__init__()

        self.themes = Proxy(ipyvuetify.Themes.Themes)


@solara.component
def ThemeToggle(
    on_icon: str = "mdi-weather-night",
    off_icon: str = "mdi-weather-sunny",
):
    """
    Insert a toggle switch for user to switch between light and dark themes.

    ```solara
    import solara.lab

    @solara.component
    def Page():
        solara.lab.ThemeToggle()
    ```

    ## Arguments
    - `dark`: A boolean value indicating whether the dark theme is enabled. Defaults to a predefined reactive variable set in `solara.server.settings`,
        `dark = solara.reactive(settings.theme.variant == ThemeVariant.dark)`.
    - `on_icon`: The icon to display when the dark theme is enabled.
    - `off_icon`: The icon to display when the dark theme is disabled.
    """

    def set_theme(*args):
        theme.dark = not theme.dark

    solara.v.Checkbox(on_icon=on_icon, off_icon=off_icon, v_model=theme.dark, on_v_model=set_theme)


theme = Proxy(Theme)

ipyvuetify.Themes.theme = theme
