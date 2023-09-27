import os
from pathlib import Path
from typing import Optional

import solara.settings

os.environ["MY_VALUE"] = "test"
os.environ["SOLARA_test_some_int"] = "42"
os.environ["SOLARA_test_some_bool"] = "true"
os.environ["SOLARA_test_value_no_field"] = "42"
os.environ["SOLARA_test_path"] = "/tmp/test"
os.environ["SOLARA_test_path_optional"] = "/tmp/test/optional"


class MySettings(solara.settings.BaseSettings):
    value: str = solara.settings.Field("default1", env="MY_VALUE")
    other_value: str = solara.settings.Field("default2", env="OTHER_VALUE")
    some_int: int = solara.settings.Field(128)
    some_other_int: int = solara.settings.Field(128)
    some_bool: bool = solara.settings.Field(False)
    some_other_bool: bool = solara.settings.Field(False)

    value_no_field: int = 50
    value_no_field_other: int = 50

    path: Path = Path("/tmp")
    path_optional: Optional[Path] = None

    class Config:
        env_prefix = "solara_test_"


def test_settings():
    settings = MySettings()
    assert settings.value == "test"
    assert settings.other_value == "default2"
    assert settings.some_int == 42
    assert settings.some_other_int == 128
    assert settings.some_bool is True
    assert settings.some_other_bool is False
    assert settings.value_no_field == 42
    assert settings.value_no_field_other == 50
    assert settings.path == Path("/tmp/test")
    assert settings.path_optional == Path("/tmp/test/optional")


def test_dict():
    settings = MySettings()
    test_value = "some-other-value"
    settings.value = test_value
    assert settings.dict()["value"] == test_value
