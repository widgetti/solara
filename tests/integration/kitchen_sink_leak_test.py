"""Object-level leak check for the kitchen-sink measurement app.

The memory harness (docs/memory-measurement) showed a sawtooth memory pattern
for kitchen_sink_app.py. This test decides "true leak vs delayed collection":
it renders the app, exercises every feature (3 clicks + ALL-DONE marker),
closes the page, waits for the kernel cull, forces GC, and asserts the kernel
context and kernel are collected. If they are, the sawtooth is cyclic garbage
waiting for a gen-2 GC, not a leak.
"""

import gc
import threading
import time
import weakref
from pathlib import Path

import playwright.sync_api
import pytest

import solara
import solara.server.kernel_context

HERE = Path(__file__).parent
APP = HERE.parent.parent / "docs" / "memory-measurement" / "kitchen_sink_app.py"


@pytest.fixture
def no_cull_timeout():
    cull_timeout_previous = solara.server.settings.kernel.cull_timeout
    solara.server.settings.kernel.cull_timeout = "0.0001s"
    try:
        yield
    finally:
        solara.server.settings.kernel.cull_timeout = cull_timeout_previous


def _scoped(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app(str(APP)):
        page_session.goto(solara_server.base_url)
        button = page_session.locator("button:has-text('Clicked')")
        button.wait_for()
        for i in range(3):
            button.click()
            page_session.locator(f"button:has-text('Clicked: {i + 1}')").wait_for()
        page_session.locator("text=ALL-DONE").wait_for()

        assert len(solara.server.kernel_context.contexts) == 1
        ctx = list(solara.server.kernel_context.contexts.values())[0]
        context_ref = weakref.ref(ctx)
        kernel_ref = weakref.ref(ctx.kernel)
        shell = ctx.kernel.shell
        shell_ref = weakref.ref(shell)
        last_cull_task = ctx._last_kernel_cull_task
        page_session.goto("about:blank")
        if last_cull_task is not None and not last_cull_task.done():
            event = threading.Event()
            last_cull_task.add_done_callback(lambda _: event.set())
            assert event.wait(10)
        closed_event = ctx.closed_event
        assert closed_event.wait(10)
        del ctx, last_cull_task, closed_event
        if shell_ref():
            del shell_ref().__dict__
        del shell
    return context_ref, kernel_ref, shell_ref


def test_kitchen_sink_no_leak(
    pytestconfig,
    browser: playwright.sync_api.Browser,
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    no_cull_timeout,
):
    context_ref, kernel_ref, shell_ref = _scoped(page_session, solara_server, solara_app)
    page_session.context.tracing.stop()

    import logging

    def clear_captured_log_records():
        # pytest's LogCaptureHandler retains LogRecords whose exc_info tracebacks can
        # reference the kernel context (e.g. the asyncio "Exception in callback" ERROR
        # from the task-cancel race, or solara's own logger.exception in the task thread).
        # Production has no such handler, so that retention is a test artifact. Records
        # can be emitted at any point while background task threads wind down, so clear
        # continuously, not once.
        for logger_obj in [logging.getLogger()] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]:
            for handler in getattr(logger_obj, "handlers", []):
                if hasattr(handler, "records"):
                    handler.records.clear()

    for i in range(200):
        time.sleep(0.1)
        clear_captured_log_records()
        for gen in [2, 1, 0]:
            gc.collect(gen)
        if context_ref() is None and kernel_ref() is None and shell_ref() is None:
            break
    else:
        import objgraph

        for name, ref in [("context", context_ref), ("kernel", kernel_ref), ("shell", shell_ref)]:
            obj = ref()
            if obj is None:
                continue
            print(f"--- retention chain for leaked {name} ---")  # noqa
            chain = objgraph.find_backref_chain(obj, objgraph.is_proper_module, max_depth=50)
            for i, item in enumerate(chain):
                type_name = type(item).__name__
                if hasattr(item, "__name__"):
                    type_name += f" ({item.__name__})"
                print(f"  [{i:2d}] {type_name}")  # noqa
            # objgraph found no module root: dump raw referrers two levels deep
            if len(chain) <= 1:
                import reprlib

                short = reprlib.Repr()
                short.maxstring = 120
                short.maxother = 120
                for r1 in gc.get_referrers(obj):
                    if r1 is chain:
                        continue
                    print(f"  referrer L1: {type(r1).__name__}: {short.repr(r1)}")  # noqa
                    for r2 in gc.get_referrers(r1):
                        print(f"      referrer L2: {type(r2).__name__}: {short.repr(r2)}")  # noqa

    assert context_ref() is None
    assert kernel_ref() is None
    assert shell_ref() is None
