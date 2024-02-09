from typing import Callable

import ipyvuetify.Themes
from ipyvuetify.Themes import Theme

import solara
import solara.server.settings as settings
from solara.components.component_vue import component_vue
from solara.tasks import Proxy

theme = Proxy(Theme)
ipyvuetify.Themes.theme = theme


@component_vue("theming.vue")
def _ThemeToggle(
    theme_effective: str,
    event_sync_themes: Callable[[str], None],
    enable_auto: bool,
    on_icon: str,
    off_icon: str,
    auto_icon: str,
):
    pass


@solara.component
def ThemeToggle(
    on_icon: str = "mdi-weather-night",
    off_icon: str = "mdi-weather-sunny",
    auto_icon: str = "mdi-brightness-auto",
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
    - `on_icon`: The icon to display when the dark theme is enabled.
    - `off_icon`: The icon to display when the dark theme is disabled.
    - `auto_icon`: The icon to display when the theme is set to auto
        (**note**: auto mode is only available if the server settings `theme.variant_user_selectable` is enabled).
    """

    def sync_themes(selected_theme: str):
        theme.dark = selected_theme

    return _ThemeToggle(
        theme_effective=theme.dark,
        event_sync_themes=sync_themes,
        enable_auto=settings.theme.variant_user_selectable,
        on_icon="mdi-weather-night",
        off_icon="mdi-weather-sunny",
        auto_icon="mdi-brightness-auto",
    )
