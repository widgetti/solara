import contextlib
import sys

import pytest

import solara.server.settings

solara.server.settings.telemetry.mixpanel_token = "adbf863d17cba80db608788e7fce9843"


@pytest.fixture
def extra_include_path():
    @contextlib.contextmanager
    def extra_include_path(path):
        sys.path.insert(0, str(path))
        try:
            yield
        finally:
            sys.path[:] = sys.path[1:]

    return extra_include_path
