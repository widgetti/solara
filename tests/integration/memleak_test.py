import gc
import time
import weakref
from pathlib import Path
from typing import Optional

import objgraph
import playwright.sync_api
import pytest

import solara
import solara.server.kernel_context

HERE = Path(__file__).parent


set_value = None
context: Optional["solara.server.kernel_context.VirtualKernelContext"] = None


@pytest.fixture
def no_cull_timeout():
    cull_timeout_previous = solara.server.settings.kernel.cull_timeout
    solara.server.settings.kernel.cull_timeout = "0.0001s"
    try:
        yield
    finally:
        solara.server.settings.kernel.cull_timeout = cull_timeout_previous


def _scoped_test_memleak(
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    extra_include_path,
):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Examples").first.wait_for()
        assert len(solara.server.kernel_context.contexts) == 1
        context = weakref.ref(list(solara.server.kernel_context.contexts.values())[0])
        # we should not have created a new context
        assert len(solara.server.kernel_context.contexts) == 1
        kernel = weakref.ref(context().kernel)
        shell = weakref.ref(kernel().shell)
        session = weakref.ref(kernel().session)
        page_session.goto("about:blank")
        assert context().closed_event.wait(10)
        if shell():
            del shell().__dict__
    return context, kernel, shell, session


def test_memleak(
    pytestconfig,
    request,
    browser: playwright.sync_api.Browser,
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    extra_include_path,
    no_cull_timeout,
):
    # for unknown reasons, del does not work in CI
    context_ref, kernel_ref, shell_ref, session_ref = _scoped_test_memleak(page_session, solara_server, solara_app, extra_include_path)

    for i in range(200):
        time.sleep(0.1)
        for gen in [2, 1, 0]:
            gc.collect(gen)
        if context_ref() is None and kernel_ref() is None and shell_ref() is None and session_ref() is None:
            break
    else:
        name = solara_server.__class__.__name__
        output_path = Path(pytestconfig.getoption("--output")) / f"mem-leak-{name}.pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print("output to", output_path, output_path.resolve())  # noqa
        objgraph.show_backrefs([context_ref(), kernel_ref(), shell_ref(), session_ref()], filename=str(output_path), max_depth=15, too_many=15)

    assert context_ref() is None
    assert kernel_ref() is None
    assert shell_ref() is None
    assert session_ref() is None
