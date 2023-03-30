import sys

import ipywidgets as widgets
import pytest

from solara.server import app, kernel


# with python 3.6 we don't use the comm package
@pytest.mark.skipif(sys.version_info < (3, 7, 0), reason="ipykernel version too low")
def test_widget_error_message_outside_context(no_app_context):
    from ipyvuetify.Themes import theme

    theme.get_state()
    kernel_shared = kernel.Kernel()
    context1 = app.AppContext(id="1", kernel=kernel_shared)
    with pytest.raises(RuntimeError):
        with context1:
            assert theme.model_id


def test_widget_dict(no_app_context):
    kernel_shared = kernel.Kernel()
    context1 = app.AppContext(id="1", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})
    context2 = app.AppContext(id="2", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})

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
