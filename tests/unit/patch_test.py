import ipywidgets as widgets

from solara.server import app, kernel, patch

patch.patch()


def test_widget_dict():
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
