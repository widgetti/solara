from typing import Optional

import pydantic


class MainSettings(pydantic.BaseSettings):
    use_pdb: bool = False
    loader: str = "solara"
    dark: Optional[bool] = None

    class Config:
        env_prefix = "solara_"
        case_sensitive = False
        env_file = ".env"


main = MainSettings()
