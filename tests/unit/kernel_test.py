import json
from datetime import datetime
from unittest.mock import Mock

import pytest

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


def test_reconnect_moves_the_kernel_to_the_event_loop_of_the_new_connection(no_kernel_context):
    import asyncio

    from solara.server import kernel_context

    def connect_on_its_own_loop():
        # threaded mode: each websocket connection runs on an event loop of its own
        loop = asyncio.new_event_loop()

        async def connect():
            return kernel_context.initialize_virtual_kernel("session-loop", "kernel-loop", Mock())

        return loop.run_until_complete(connect()), loop

    context, first_loop = connect_on_its_own_loop()
    second_loop = None
    try:
        assert context.event_loop is first_loop
        first_loop.close()  # the websocket disconnected, and its loop with it
        reconnected, second_loop = connect_on_its_own_loop()
        assert reconnected is context
        assert context.event_loop is second_loop
    finally:
        if second_loop is not None:
            second_loop.close()
        for live_context in list(kernel_context.contexts.values()):
            live_context.close()


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
