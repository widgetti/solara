import json
from datetime import datetime
from unittest.mock import Mock

from solara.server.kernel import SessionWebsocket
import numpy as np


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


def test_on_close_registration_during_close_runs(no_kernel_context):
    # a close callback can create another per-kernel resource that registers its
    # own on_close (e.g. a lazy factory re-created during teardown). Iterating the
    # live callback list with reversed() silently skipped registrations that
    # arrived mid-drain — the cleanup never ran, occasionally leaving a whole
    # kernel's subscriptions behind. The drain must also run late arrivals.
    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="onclose-nested", kernel=kernel_mod.Kernel(), session_id="onclose-session")
    ran = []

    def outer():
        context.on_close(lambda: ran.append("nested"))
        ran.append("outer")

    with context:
        context.on_close(outer)
    context.close()
    assert ran == ["outer", "nested"]
    # and registrations after close run immediately
    context.on_close(lambda: ran.append("late"))
    assert ran == ["outer", "nested", "late"]


def test_on_close_check_then_append_race_does_not_lose_callback(no_kernel_context):
    # on_close() reads _on_close_callbacks_drained and THEN appends, non-atomically,
    # while close() drains lock-free. A registrant that reads the flag as False can be
    # preempted; close() then finishes BOTH drains and sets the flag; the registrant
    # resumes and appends into a list nobody will ever drain -> the callback is lost.
    # For a fresh AutoSubscribeContextManager.unsubscribe_all registered this way, the
    # kernel's subscriptions leak under a dead context. Deterministic: block the
    # registrant inside append until close() has fully returned.
    import threading

    from solara.server import kernel as kernel_mod
    from solara.server.kernel_context import VirtualKernelContext

    context = VirtualKernelContext(id="onclose-race", kernel=kernel_mod.Kernel(), session_id="onclose-race-session")

    in_append = threading.Event()
    may_proceed = threading.Event()

    class BlockingAppendList(list):
        armed = False

        def append(self, item):
            if self.armed:
                self.armed = False  # only the first (raced) append blocks
                in_append.set()
                assert may_proceed.wait(timeout=5)
            super().append(item)

    blocking = BlockingAppendList()
    blocking.extend(context._on_close_callbacks)  # preserve any on_kernel_start cleanups
    context._on_close_callbacks = blocking

    ran = []

    def register():
        # reads _on_close_callbacks_drained == False, then blocks inside append
        context.on_close(lambda: ran.append("raced"))

    blocking.armed = True
    t = threading.Thread(target=register)
    t.start()
    assert in_append.wait(timeout=5)  # registrant read the flag False, now stuck in append

    context.close()  # drains, sets the flag, second drain (empty), returns

    may_proceed.set()  # let the append land AFTER close has finished
    t.join(timeout=5)
    assert not t.is_alive()

    # the raced callback must still run: a correct on_close rechecks the drained flag
    # after appending and runs the cleanup if close() finished in the meantime.
    assert ran == ["raced"]
