"""
# Themes in Solara

Theming is provided to Solara through the `ipyvuetify` package. Two themes are provided by default: light and dark.
Control over the theme variant is provided to the user through the `ThemeToggle` component.

## Themes

The default themes can be customized through altering `solara.lab.theme`. The [theme options of vuetify]
(https://v2.vuetifyjs.com/en/features/theme/#customizing)
are available as `solara.lab.theme.themes.light` and `solara.lab.theme.themes.dark`. The different properties of the theme can be set through, for example

```python
solara.lab.theme.themes.light.primary = "#3f51b5"
```

Dark theme can be enabled/disabled through `solara.lab.theme.dark = True` / `False`.

**important**: In order for the custom theme to take effect, it needs to be included in the page, for example by using the `solara.lab.NonVisual` component.

## ThemeToggle

"""

import solara
from solara.website.utils import apidoc

from . import NoPage

title = "Themes"
Page = NoPage
__doc__ += apidoc(solara.lab.ThemeToggle)  # type: ignore
