import contextlib
import sys

import pytest


@pytest.fixture
def extra_include_path():
    @contextlib.contextmanager
    def extra_include_path(path):
        sys.path.insert(0, path)
        try:
            yield
        finally:
            sys.path[:] = sys.path[1:]

    return extra_include_path
