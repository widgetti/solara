from typing import Callable, cast

import ipyvuetify.Themes
from ipyvuetify.Themes import Theme

import solara
from solara.components.component_vue import component_vue
from solara.tasks import Proxy

theme = Proxy(Theme)
ipyvuetify.Themes.theme = cast(ipyvuetify.Themes.Theme, theme)


@component_vue("theming.vue")
def _ThemeToggle(
    theme_dark: str,
    event_sync_themes: Callable[[str], None],
    enable_auto: bool,
    on_icon: str,
    off_icon: str,
    auto_icon: str,
    clicks: int = 1,
):
    pass


@solara.component
def ThemeToggle(
    on_icon: str = "mdi-weather-night",
    off_icon: str = "mdi-weather-sunny",
    auto_icon: str = "mdi-brightness-auto",
    enable_auto: bool = True,
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
    - `auto_icon`: The icon to display when the theme is set to auto. Only visible if `enable_auto` is `True`.
    - `enable_auto`: Whether to enable the auto detection of dark mode.
    """

    def sync_themes(selected_theme: str):
        theme.dark = selected_theme

    return _ThemeToggle(
        theme_dark=theme.dark,
        event_sync_themes=sync_themes,
        enable_auto=enable_auto,
        on_icon=on_icon,
        off_icon=off_icon,
        auto_icon=auto_icon,
    )
