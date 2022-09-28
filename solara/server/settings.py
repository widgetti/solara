from enum import Enum

import pydantic


class ThemeVariant(str, Enum):
    light = "light"
    dark = "dark"
    auto = "auto"


class ThemeSettings(pydantic.BaseSettings):
    variant: ThemeVariant = ThemeVariant.light
    variant_user_selectable: bool = True
    loader: str = "solara"

    class Config:
        env_prefix = "solara_theme_"
        case_sensitive = False
        env_file = ".env"


class MainSettings(pydantic.BaseSettings):
    use_pdb: bool = False
    mode: str = "production"
    tracer: bool = False
    timing: bool = False

    class Config:
        env_prefix = "solara_"
        case_sensitive = False
        env_file = ".env"


main = MainSettings()
theme = ThemeSettings()
