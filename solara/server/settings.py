import pydantic


class MainSettings(pydantic.BaseSettings):
    use_pdb: bool = False
    loader: str = "solara"
    dark: bool = False

    class Config:
        env_prefix = "solara_"
        case_sensitive = False
        env_file = ".env"


main = MainSettings()
