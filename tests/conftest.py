import contextlib
import sys

import pytest
from dotenv import load_dotenv

import solara.server.reload
import solara.server.settings

load_dotenv()  # take environment variables from .env.  should be in os.environ for the whole test

solara.server.settings.telemetry.mixpanel_token = "adbf863d17cba80db608788e7fce9843"
solara.server.settings.main.mode = "development"
solara.server.reload.reloader.watcher = solara.server.reload.WatcherType([], solara.server.reload.reloader._on_change)


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
