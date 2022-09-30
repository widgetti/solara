import threading

import solara
import solara.hooks as hooks
import traitlets
from ipyvue import Template
from ipyvuetify.extra import FileInput
from ipywidgets import widget_serialization


class FileDropZone(FileInput):
    # override to narrow traitlet of FileInput
    template = traitlets.Instance(Template).tag(sync=True, **widget_serialization)
    template_file = (__file__, "file_drop.vue")
    items = traitlets.List(default_value=[]).tag(sync=True)
    label = traitlets.Unicode().tag(sync=True)


@solara.component
def FileDrop(on_total_progress, on_file, label="Drop file here"):
    file_info, set_file_info = solara.use_state(None)
    wired_files, set_wired_files = solara.use_state(None)

    file_drop = FileDropZone.element(label=label, on_total_progress=on_total_progress, on_file_info=set_file_info)

    def wire_files():
        if not file_info:
            return

        real = solara.get_widget(file_drop)

        # workaround for @observe being cleared
        real.version += 1
        real.reset_stats()

        set_wired_files(real.get_files())

    solara.use_side_effect(wire_files, [file_info])

    def handle_file(cancel: threading.Event):
        if not wired_files:
            return

        on_file(wired_files[0])

    hooks.use_thread(handle_file, [wired_files])

    return file_drop
