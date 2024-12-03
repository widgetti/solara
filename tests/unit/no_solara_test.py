import ipywidgets as widgets
from IPython.display import display

import solara.components.file_download

# test if normal widget code works with no app context


def test_create_widget(no_kernel_context):
    button = widgets.Button(description="Click me")
    button.layout.close()
    button.close()


def test_vue_template(no_kernel_context):
    widget = solara.components.file_download.FileDownloadWidget()
    widget.close()


def test_display(no_kernel_context):
    display("test")
