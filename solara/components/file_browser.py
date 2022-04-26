import os
from os.path import isfile, join
from typing import List, Optional, cast

import humanize
import ipyvuetify as vy
import react_ipywidgets as react
import traitlets

from solara.components import Div


def list_dir(path):
    def mk_item(n):
        full_path = join(path, n)
        is_file = isfile(full_path)
        return {"name": n, "is_file": is_file, "size": humanize.naturalsize(os.stat(full_path).st_size) if is_file else None}

    files = [mk_item(n) for n in os.listdir(path) if not n.startswith(".")]
    sorted_files = sorted(files, key=lambda item: ("0" if item["is_file"] else "1") + item["name"].lower())
    return sorted_files


class FileListWidget(vy.VuetifyTemplate):
    template_file = (__file__, "file_list_widget.vue")

    files = traitlets.List().tag(sync=True)
    selected = traitlets.Dict(allow_none=True, default_value=None).tag(sync=True)
    scroll_pos = traitlets.Int(allow_none=True).tag(sync=True)


@react.component
def FileBrowser(start_directory, on_file_name):
    current_dir, set_current_dir = react.use_state(start_directory)
    selected, set_selected = react.use_state(None)
    warning, set_warning = react.use_state(cast(Optional[str], None))
    scroll_pos_stack, set_scroll_pos_stack = react.use_state(cast(List[int], []))
    scroll_pos, set_scroll_pos = react.use_state(0)

    def change_dir(new_dir):
        if os.access(new_dir, os.R_OK):
            set_current_dir(new_dir)
            set_warning(None)
            return True
        else:
            set_warning(f"[no read access to {new_dir}]")

    def on_selected(item):
        if item is None:
            return
        if item["name"] == "..":
            new_dir = current_dir[: current_dir.rfind(os.path.sep)]
            if change_dir(new_dir) and scroll_pos_stack:
                last_pos = scroll_pos_stack[-1]
                set_scroll_pos_stack(scroll_pos_stack[:-1])
                set_scroll_pos(last_pos)
            set_selected(None)
            return

        path = os.path.join(current_dir, item["name"])
        if item["is_file"]:
            on_file_name(path)
        else:
            if change_dir(path):
                set_scroll_pos_stack(scroll_pos_stack + [scroll_pos])
                set_scroll_pos(0)

        set_selected(None)

    with Div(class_="solara-file-browser") as main:
        Div(children=[current_dir])
        FileListWidget.element(
            files=[{"name": "..", "is_file": False}] + list_dir(current_dir),
            selected=selected,
            on_selected=on_selected,
            scroll_pos=scroll_pos,
            on_scroll_pos=set_scroll_pos,
        ).key("FileList")
        if warning:
            Div(style_="font-weight: bold; color: red", children=[warning])

    return main
