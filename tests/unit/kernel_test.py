import json
import logging
import threading
from datetime import datetime
from unittest.mock import Mock

import numpy as np
import pytest

from solara.server.kernel import SessionWebsocket


def test_session_datetime():
    # some libraries, such as plotly may put datetime objects in the json content
    class Dummy:
        pass

    websocket = Mock()
    stream = Dummy()
    stream.channel = "iopub"  # type: ignore
    session = SessionWebsocket()
    session.websockets.add(websocket)
    session.send(stream, {"msg_type": "test", "content": {"data": "test"}, "somedate": datetime.now()})  # type: ignore
    websocket.send.assert_called_once()


def test_numpy_scalar():
    class Dummy:
        pass

    websocket = Mock()
    stream = Dummy()
    stream.channel = "iopub"  # type: ignore
    session = SessionWebsocket()
    session.websockets.add(websocket)
    v = np.int64(42)
    session.send(stream, {"msg_type": "test", "content": {"a_numpy_scalar": v}})  # type: ignore
    websocket.send.assert_called_once()
    json_string = websocket.send.call_args[0][0]
    json_data = json.loads(json_string)
    assert json_data["content"]["a_numpy_scalar"] == 42


def test_comm_close_after_kernel_closed(kernel_context, no_kernel_context):
    # A widget can be closed after its kernel closed (__del__ when the garbage
    # collector finds it) or from a thread bound to a different kernel: the
    # context-based get_comm_manager() then resolves to a manager that never
    # registered the comm, and upstream unregister_comm raises KeyError. That
    # noise surfaces as unraisable exceptions burying real errors in teardown
    # output; closing a comm must be safe regardless of the current context.
    import comm

    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="comm-close", kernel=kernel_mod.Kernel(), session_id="comm-close-session")
    with context:
        c = comm.create_comm(target_name="test")
    # outside the context now: get_comm_manager() resolves to the global manager,
    # which never saw this comm
    c.close()


def test_on_close_registration_during_and_after_close(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="onclose-nested", kernel=kernel_mod.Kernel(), session_id="session")
    ran = []
    nested_resources = []
    app = object()
    context.app_object = app

    def nested():
        nested_resources.append((context.kernel is not None, context.app_object is app))
        ran.append("nested")

    def outer():
        context.on_close(nested)
        ran.append("outer")

    context.on_close(outer)
    context.close()
    assert ran == ["outer", "nested"]
    assert nested_resources == [(True, True)]

    context.on_close(lambda: ran.append("late"))
    assert ran[-1] == "late"


def test_on_close_registration_racing_close_runs(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="onclose-race", kernel=kernel_mod.Kernel(), session_id="session")
    append_started = threading.Event()
    release_append = threading.Event()

    class BlockingAppendList(list):
        armed = True

        def append(self, item):
            if self.armed:
                self.armed = False
                append_started.set()
                assert release_append.wait(timeout=5)
            super().append(item)

    context._on_close_callbacks = BlockingAppendList(context._on_close_callbacks)
    ran = []
    register = threading.Thread(target=lambda: context.on_close(lambda: ran.append("raced")))
    closer = threading.Thread(target=context.close)

    register.start()
    assert append_started.wait(timeout=5)
    closer.start()
    release_append.set()
    register.join(timeout=5)
    closer.join(timeout=5)

    assert not register.is_alive()
    assert not closer.is_alive()
    assert ran == ["raced"]


def test_restart_registration_belongs_to_next_generation(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="restart-epoch", kernel=kernel_mod.Kernel(), session_id="session")
    ran = []

    def cleanup():
        ran.append("old")
        context.on_close(lambda: ran.append("next"))

    context.on_close(cleanup)
    context.restart()
    assert ran == ["old"]
    context.restart()
    assert ran == ["old", "next"]
    context.close()


def test_restart_callback_can_request_close_from_worker(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="restart-close", kernel=kernel_mod.Kernel(), session_id="session")
    requested = threading.Event()

    def cleanup():
        if requested.is_set():
            return
        requested.set()
        closer = threading.Thread(target=context.close)
        closer.start()
        closer.join(timeout=5)
        assert not closer.is_alive()

    context.on_close(cleanup)
    context.restart()
    assert context.closed_event.wait(timeout=5)

    context.__post_init__ = Mock()  # type: ignore
    context.restart()
    context.__post_init__.assert_not_called()  # type: ignore


def test_reconnect_replaces_context_closing_during_restart(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server import kernel_context

    context = kernel_context.VirtualKernelContext(id="restart-reconnect", kernel=kernel_mod.Kernel(), session_id="session")
    kernel_context.contexts[context.id] = context
    cleanup_started = threading.Event()
    release_cleanup = threading.Event()

    def cleanup():
        cleanup_started.set()
        assert release_cleanup.wait(timeout=5)

    context.on_close(cleanup)
    restart = threading.Thread(target=context.restart)
    restart.start()
    assert cleanup_started.wait(timeout=5)
    context.close()
    try:
        replacement = kernel_context.initialize_virtual_kernel(context.session_id, context.id, Mock())
        assert replacement is not context
        replacement.page_connect("reconnected")
    finally:
        release_cleanup.set()
        restart.join(timeout=5)
        assert not restart.is_alive()
        for live_context in list(kernel_context.contexts.values()):
            live_context.close()


def test_close_is_reentrant_and_cleanup_runs_once(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="close-reentrant", kernel=kernel_mod.Kernel(), session_id="session")
    ran = []

    def cleanup():
        ran.append("cleanup")
        context.close()

    context.on_close(cleanup)
    context.close()
    context.close()

    assert ran == ["cleanup"]
    assert context.closed_event.is_set()


def test_close_callbacks_are_unlocked_and_failure_isolated(no_kernel_context, caplog):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="close-callbacks", kernel=kernel_mod.Kernel(), session_id="session")
    acquired = threading.Event()

    def acquire_context_lock():
        with context.lock:
            acquired.set()

    def callback():
        thread = threading.Thread(target=acquire_context_lock)
        thread.start()
        thread.join(timeout=5)
        assert not thread.is_alive()

    def fail():
        raise RuntimeError("cleanup failed")

    context.on_close(callback)
    context.on_close(fail)
    with caplog.at_level(logging.ERROR):
        context.close()

    assert acquired.is_set()
    assert context.closed_event.is_set()
    assert "cleanup failed" in caplog.text


def test_page_connect_is_rejected_once_close_starts(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="closing-page", kernel=kernel_mod.Kernel(), session_id="session")
    started = threading.Event()
    release = threading.Event()
    context.state_flush_worker = Mock()

    def teardown(reason):
        started.set()
        assert release.wait(timeout=5)

    context._teardown_persistence = teardown  # type: ignore
    closer = threading.Thread(target=context.close)
    closer.start()
    assert started.wait(timeout=5)
    with pytest.raises(RuntimeError, match="closed kernel"):
        context.page_connect("late")
    release.set()
    closer.join(timeout=5)
    assert not closer.is_alive()


def test_restart_cleanup_failure_does_not_skip_cleanup_or_reinit(no_kernel_context, caplog):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="restart-error", kernel=kernel_mod.Kernel(), session_id="session")
    context._on_close_callbacks = []
    ran = []
    context.__post_init__ = lambda: ran.append("started")  # type: ignore
    context.on_close(lambda: ran.append("older"))

    def fail():
        raise RuntimeError("cleanup failed")

    context.on_close(fail)
    context.on_close(lambda: ran.append("newer"))
    with caplog.at_level(logging.ERROR):
        context.restart()

    assert ran == ["newer", "older", "started"]
    context.close()


def test_restart_initialization_error_does_not_wedge_close(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="restart-init-error", kernel=kernel_mod.Kernel(), session_id="session")

    def fail():
        raise RuntimeError("restart initialization failed")

    context.__post_init__ = fail  # type: ignore
    with pytest.raises(RuntimeError, match="restart initialization failed"):
        context.restart()

    context.close()
    assert context.closed_event.wait(timeout=5)


def test_generation_value_destructor_runs_outside_lifecycle_lock(no_kernel_context):
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="generation-del", kernel=kernel_mod.Kernel(), session_id="session")
    destroyed = threading.Event()

    class Value:
        def __del__(self):
            context.on_close(lambda: None)
            destroyed.set()

    class Store:
        storage_key = "owned"

    store = Store()
    context.track_generation_store(store)
    context.user_dicts["owned"] = Value()  # type: ignore[assignment]
    thread = threading.Thread(target=context.restart)
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert destroyed.is_set()
    del store
    context.close()


def test_comm_info_request_filters_on_target_name():
    # The widget manager's fetchAll (_loadFromKernel) asks for comms with
    # target_name="jupyter.widget" and then sends request_state to every comm id
    # in the reply. The solara.control comm (run/reload/app-status) must therefore
    # never appear in that reply: it does not speak the widget protocol, so each
    # leaked id produces an "Unknown comm method called on solara.control comm:
    # request_state" error on the server (seen in production since the reconnect
    # state machine started calling fetchAll on every hot reconnect).
    from unittest.mock import Mock

    from solara.server import kernel as kernel_mod
    from solara.server.server import process_kernel_messages

    kernel = kernel_mod.Kernel()
    try:
        websocket = Mock()
        kernel.session.websockets.add(websocket)
        kernel.shell_stream = kernel_mod.WebsocketStreamWrapper(websocket, "shell")
        kernel.comm_manager.comms["widget-comm-id"] = Mock(target_name="jupyter.widget")  # type: ignore
        kernel.comm_manager.comms["control-comm-id"] = Mock(target_name="solara.control")  # type: ignore

        msg = kernel.session.msg("comm_info_request", content={"target_name": "jupyter.widget"})
        msg["channel"] = "shell"
        process_kernel_messages(kernel, msg)

        replies = [json.loads(call.args[0]) for call in websocket.send.call_args_list]
        comm_info_replies = [m for m in replies if m["header"]["msg_type"] == "comm_info_reply"]
        assert len(comm_info_replies) == 1
        comms = comm_info_replies[0]["content"]["comms"]
        assert comms == {"widget-comm-id": {"target_name": "jupyter.widget"}}
    finally:
        kernel.comm_manager.comms.clear()  # type: ignore
        kernel.close()
