import contextlib
import sys

import pytest

from solara.server import kernel, patch
from solara.server.app import AppContext


@pytest.fixture(scope="session")
def solara_patched():
    patch.patch()


@pytest.fixture(autouse=True)
def app_context(solara_patched):
    kernel_shared = kernel.Kernel()
    context = AppContext(id="1", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})
    try:
        with context:
            yield context
    finally:
        with context:
            context.close()


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
