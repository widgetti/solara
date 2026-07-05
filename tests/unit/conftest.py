import os
import sys

import pytest

import solara.server.app
import solara.server.kernel_context
from solara.server import kernel
from solara.server.kernel_context import VirtualKernelContext


_exitstatus = 0


def pytest_sessionfinish(session, exitstatus):
    global _exitstatus
    _exitstatus = int(exitstatus)


def pytest_unconfigure(config):
    # On Windows CI, lingering non-daemon threads (from websockets/ipykernel)
    # keep the Python process alive for hours after pytest has reported all
    # tests passed. Force-exit with the correct status so the job completes.
    # This must happen in pytest_unconfigure, not pytest_sessionfinish: sessionfinish hooks run
    # *inside* the terminal reporter's hookwrapper, so exiting there kills pytest before the
    # FAILURES section and summary are printed (which made Windows CI failures undiagnosable).
    if sys.platform == "win32" and os.environ.get("CI"):
        # os._exit skips buffer flushing, and stdout is block-buffered on CI (a pipe)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(_exitstatus)


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
