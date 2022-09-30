"""
# FileBrowser

Browse file (and directories) at the server side.

There are two modes possible

   * `can_select=False`
      * `on_file_open`: Triggered when **single** clicking a file or directoy.
      * `on_path_select`: Never triggered
      * `on_directory_change`: Triggered when clicking a directory
   * `can_select=True`
      * `on_file_open`: Triggered when **double** clicking a file or directoy.
      * `on_path_select`: Triggered when clicking a file or directoy
      * `on_directory_change`: Triggered when double clicking a directory

"""
from pathlib import Path
from typing import Optional, cast

import solara


@solara.component
def Page():
    file, set_file = solara.use_state(cast(Optional[Path], None))
    path, set_path = solara.use_state(cast(Optional[Path], None))
    directory, set_directory = solara.use_state(Path("~").expanduser())

    with solara.VBox() as main:
        can_select = solara.ui_checkbox("Enable select")

        def reset_path():
            set_path(None)
            set_file(None)

        # reset path and file when can_select changes
        solara.use_memo(reset_path, [can_select])
        solara.FileBrowser(directory, on_directory_change=set_directory, on_path_select=set_path, on_file_open=set_file, can_select=can_select)
        solara.Info(f"You are in directory: {directory}")
        solara.Info(f"You selected path: {path}")
        solara.Info(f"You opened file: {file}")
    return main
