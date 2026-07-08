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
