from unittest.mock import Mock

import IPython.display

from solara.server import kernel, kernel_context


def test_shell(no_kernel_context):
    ws1 = Mock()
    ws2 = Mock()
    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    kernel1.session.websockets.add(ws1)
    kernel2.session.websockets.add(ws2)
    context1 = kernel_context.VirtualKernelContext(id="1", kernel=kernel1, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="2", kernel=kernel2, session_id="session-2")

    with context1:
        IPython.display.display("test1")
        assert ws1.send.call_count == 1
        assert ws2.send.call_count == 0
    with context2:
        IPython.display.display("test1")
        assert ws1.send.call_count == 1
        assert ws2.send.call_count == 1
