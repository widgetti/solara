from unittest.mock import Mock

import IPython.display
import ipywidgets as widgets

from solara.server import app, kernel


def test_interactive_shell(no_app_context):
    ws1 = Mock()
    ws2 = Mock()
    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    kernel1.session.websockets.add(ws1)
    kernel2.session.websockets.add(ws2)
    context1 = app.AppContext(id="1", kernel=kernel1)
    context2 = app.AppContext(id="2", kernel=kernel2)

    with context1:
        output1 = widgets.Output()
        with output1:
            IPython.display.display("test1")
        assert output1.outputs[0]["data"]["text/plain"] == "'test1'"
        assert ws1.send.call_count == 3  # create 2 widgets (layout and output) and update data
        assert ws2.send.call_count == 0
    with context2:
        output2 = widgets.Output()
        with output2:
            IPython.display.display("test2")
        assert output2.outputs[0]["data"]["text/plain"] == "'test2'"
        assert ws1.send.call_count == 3
        assert ws2.send.call_count == 3

    context1.close()
    context2.close()


def test_clear_output():
    output1 = widgets.Output()
    with output1:
        IPython.display.display("test1")
        IPython.display.clear_output()
    assert len(output1.outputs) == 0
