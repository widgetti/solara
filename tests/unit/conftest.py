import pytest

import solara.server.app
import solara.server.kernel_context
from solara.server import kernel
from solara.server.kernel_context import VirtualKernelContext


@pytest.fixture(autouse=True)
def kernel_context():
    kernel_shared = kernel.Kernel()
    context = VirtualKernelContext(id="1", kernel=kernel_shared, session_id="session-1")
    try:
        with context:
            yield context
    finally:
        with context:
            context.close()


@pytest.fixture()
def no_kernel_context(kernel_context):
    context = solara.server.kernel_context.get_current_context()
    solara.server.kernel_context.set_current_context(None)
    try:
        yield
    finally:
        solara.server.kernel_context.set_current_context(context)
