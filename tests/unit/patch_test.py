# import sys

import ipywidgets as widgets

from solara.server import kernel, kernel_context

# import pytest


# temporary disabled
# # with python 3.6 we don't use the comm package
# @pytest.mark.skipif(sys.version_info < (3, 7, 0), reason="ipykernel version too low")
# def test_widget_error_message_outside_context(no_kernel_context):
#     from ipyvuetify.Themes import theme

#     theme.get_state()
#     kernel_shared = kernel.Kernel()
#     context1 = kernel_context.VirtualKernelContext(id="1", kernel=kernel_shared, session_id="session-1")
#     with pytest.raises(RuntimeError):
#         with context1:
#             assert theme.model_id


def test_widget_dict(no_kernel_context):
    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    context1 = kernel_context.VirtualKernelContext(id="1", kernel=kernel1, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="2", kernel=kernel2, session_id="session-2")

    with context1:
        btn1 = widgets.Button(description="context1")
    with context2:
        btn2 = widgets.Button(description="context2")

    assert btn1.model_id in context1.widgets
    assert btn1.model_id not in context2.widgets
    assert btn2.model_id in context2.widgets
    assert btn2.model_id not in context1.widgets

    del btn1
    del btn2
    context1.close()
    context2.close()


def test_pool_worker_thread_does_not_pin_kernel_context(no_kernel_context):
    import gc
    import threading
    import weakref
    from concurrent.futures import ThreadPoolExecutor

    import solara.server.app  # noqa: F401 - importing applies the threading patch

    kernel1 = kernel.Kernel()
    context = kernel_context.VirtualKernelContext(id="pool-pin-1", kernel=kernel1, session_id="session-1")
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with context:
            # force the pool to spawn its worker inside the kernel context, like a
            # request handler triggering lazy pool growth
            executor.submit(lambda: None).result()
            # a directly created thread still inherits the context
            regular_thread = threading.Thread(target=lambda: None)
            assert regular_thread.current_context is context  # type: ignore
            regular_thread.current_context = None  # type: ignore
        context_ref = weakref.ref(context)
        with context:
            context.close()
        del context, kernel1, regular_thread
        gc.collect()
        # the pool worker is still alive; it must not keep the closed context alive
        assert context_ref() is None
    finally:
        executor.shutdown(wait=False)


def test_showtraceback_logs_exception_with_exc_info(no_kernel_context, caplog):
    import logging
    import traceback

    from solara.server import patch

    kernel1 = kernel.Kernel()
    context = kernel_context.VirtualKernelContext(id="showtraceback-1", kernel=kernel1, session_id="session-1")
    fake_ipython = patch.FakeIPython(context)

    with caplog.at_level(logging.ERROR, logger="solara.server.patch"):
        try:
            raise ValueError("some app error")
        except ValueError:
            fake_ipython.showtraceback()

    records = [record for record in caplog.records if record.name == "solara.server.patch"]
    assert len(records) == 1
    record = records[0]
    # the message stays short and the exception travels via exc_info, so error trackers group
    # per exception type instead of putting every uncaught exception in a single issue
    assert record.getMessage() == "Uncaught exception"
    assert record.exc_info is not None
    assert record.exc_info[0] is ValueError
    assert "some app error" in "".join(traceback.format_exception(*record.exc_info))
    context.close()


def test_fake_ipython_leaves_no_cyclic_garbage(no_kernel_context):
    import gc

    from solara.server import patch

    kernel1 = kernel.Kernel()
    context = kernel_context.VirtualKernelContext(id="fake-ipython-gc-1", kernel=kernel1, session_id="session-1")
    # matplotlib's pyplot calls these on get_ipython().events
    patch.FakeIPython(context).events.register("post_execute", lambda: None)

    gc.collect()
    gc.disable()
    try:
        for _ in range(10):
            patch.FakeIPython(context)
        # get_ipython() makes a FakeIPython per call, so one must be freed by reference counting alone
        assert gc.collect() == 0
    finally:
        gc.enable()


def test_get_ipython_reuses_one_fake_ipython_per_context(no_kernel_context):
    from solara.server import patch

    kernel1 = kernel.Kernel()
    context = kernel_context.VirtualKernelContext(id="fake-ipython-reuse-1", kernel=kernel1, session_id="session-1")
    with context:
        first = patch.get_ipython()
        assert isinstance(first, patch.FakeIPython)
        assert patch.get_ipython() is first
    context.close()
    # the FakeIPython references the context, so close drops it to break that cycle
    assert context._fake_ipython is None


def test_context_aware_thread_leaves_no_stale_context_entries(no_kernel_context):
    import threading

    import solara.server.app  # noqa: F401 - importing applies the threading patch

    kernel1 = kernel.Kernel()
    context = kernel_context.VirtualKernelContext(id="thread-dummy-1", kernel=kernel1, session_id="session-1")
    seen = []
    with context:
        thread = threading.Thread(target=lambda: seen.append(kernel_context.get_current_context()))
    keys_before = set(kernel_context.current_context)
    thread.start()
    thread.join()
    # the thread still runs in its kernel context
    assert seen == [context]
    # and it leaves no stale current_context["Dummy-..."] entries behind
    assert [key for key in set(kernel_context.current_context) - keys_before if "Dummy" in key] == []
    with context:
        context.close()
