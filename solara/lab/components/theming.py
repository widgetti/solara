from typing import Callable, Dict, Union, cast

import ipyvuetify.Themes
from ipyvuetify.Themes import Theme

import solara
from solara.components.component_vue import component_vue
from solara.tasks import Proxy

theme = Proxy(Theme)
ipyvuetify.Themes.theme = cast(ipyvuetify.Themes.Theme, theme)


def use_dark_effective():
    """Return True if the frontend is using a dark theme.

    Equivalent of

    ```python
    solara.use_trait_observe(solara.lab.theme, "dark_effective")
    ```

    See [use_trait_observe](/api/use_trait_observe).
    """
    return solara.use_trait_observe(theme, "dark_effective")


def _set_theme(themes: Union[Dict[str, Dict[str, str]], None]):
    if themes is None:
        return

    for theme_type in themes.keys():
        widget = getattr(theme.themes, theme_type)
        with widget.hold_trait_notifications():
            for k, v in themes[theme_type].items():
                setattr(widget, k, v)


def _get_theme(theme: Theme) -> Dict[str, Dict[str, str]]:
    theme_dict: Dict[str, Dict[str, str]] = cast(Dict[str, Dict[str, str]], {})
    for theme_type, theme_value in theme.themes.__dict__.items():
        theme_traits = theme_value.keys
        theme_dict[theme_type] = {}
        for trait in theme_traits:
            if not trait.startswith("_"):
                theme_dict[theme_type][trait] = getattr(theme_value, trait)
    return theme_dict


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
