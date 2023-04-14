from unittest.mock import Mock

import IPython.display

from solara.server import app, kernel


def test_shell(no_app_context):
    ws1 = Mock()
    ws2 = Mock()
    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    kernel1.session.websockets.add(ws1)
    kernel2.session.websockets.add(ws2)
    context1 = app.AppContext(id="1", kernel=kernel1)
    context2 = app.AppContext(id="2", kernel=kernel2)

    with context1:
        IPython.display.display("test1")
        assert ws1.send.call_count == 1
        assert ws2.send.call_count == 0
    with context2:
        IPython.display.display("test1")
        assert ws1.send.call_count == 1
        assert ws2.send.call_count == 1
