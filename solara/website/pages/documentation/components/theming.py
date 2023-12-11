"""
# Themes in Solara

Theming is provided to Solara through the [`ipyvuetify`](https://solara.dev/docs/understanding/ipyvuetify) package.
Two themes are provided by default: light and dark.
Control over the theme variant (light, dark, or auto) can be provided to the user through the `ThemeToggle` component. Developers can
control theming through the `solara.lab.theme` object.

## Themes

The default themes can be customized through altering `solara.lab.theme`. The
[theme options of vuetify](https://v2.vuetifyjs.com/en/features/theme/#customizing)
are available as `solara.lab.theme.themes.light` and `solara.lab.theme.themes.dark`. The different properties of the theme can be set through, for example

```python
solara.lab.theme.themes.light.primary = "#3f51b5"
```

Dark theme can be enabled/disabled through `solara.lab.theme.dark = True` / `False` / `None`. When set to `None`, the theme is set to auto,
which will follow the system theme if the user's browser supports detecting it.

When using solara server, the default theme variant can be set in the server settings through the command line interface. See
[here](https://solara.dev/docs/understanding/solara-server) for more information.

The active theme can be detected through `solara.lab.theme.dark_effective`, which is set to `True` or `False` depending on
whether dark theme is enabled or not.

## Example

```solara
import solara
import solara.lab
from solara.lab import theme as theme


def change_color(colors):
    if "purple" in colors:
        theme.themes.light.info = "#8617c2"
    else:
        theme.themes.light.info = "#2196f3"

    if "green" in colors:
        theme.themes.light.error = "#33bd65"
    else:
        theme.themes.light.error = "#ff5252"


@solara.component
def Page():
    solara.Info("Info message")
    solara.Error("Error message")

    with solara.ToggleButtonsMultiple(on_value=change_color):
        solara.Button("Change Info", value="purple")
        solara.Button("Change Error", value="green")
```

A more advanced example can be found at [the scatter app demo](https://solara.dev/apps/scatter) where
we set a plotly theme based on dark/light theme, and also set the app bar color to its default so it
responds to the theme variant change.

## ThemeToggle

"""

import solara
from solara.website.utils import apidoc

from . import NoPage

title = "Themes"
Page = NoPage
__doc__ += apidoc(solara.lab.ThemeToggle)  # type: ignore
