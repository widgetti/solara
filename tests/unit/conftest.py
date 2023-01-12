import pytest

import solara.server.app
from solara.server import kernel
from solara.server.app import AppContext


@pytest.fixture(autouse=True)
def app_context():
    kernel_shared = kernel.Kernel()
    context = AppContext(id="1", kernel=kernel_shared)
    try:
        with context:
            yield context
    finally:
        with context:
            context.close()


@pytest.fixture()
def no_app_context(app_context):
    context = solara.server.app.get_current_context()
    solara.server.app.set_current_context(None)
    try:
        yield
    finally:
        solara.server.app.set_current_context(context)
