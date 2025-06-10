"""# FileBrowser"""

from pathlib import Path
from typing import Optional, cast
import random
import solara
from solara.website.utils import apidoc

opened = solara.reactive(cast(Optional[Path], None))
selected = solara.reactive(cast(Optional[Path], None))
directory = solara.reactive(Path("~").expanduser())
can_select = solara.reactive(False)


@solara.component
def Page():
    def reset_path():
        opened.value = None
        selected.value = None

    def select_random_file():
        files = list(directory.value.glob("*"))
        if files:
            selected.value = random.choice(files)

    # reset path and file when can_select changes
    solara.use_memo(reset_path, [can_select.value])
    solara.Checkbox(label="Enable select", value=can_select)
    solara.FileBrowser(directory, selected=selected, on_file_open=opened.set, can_select=can_select.value)
    solara.Info(f"You are in directory: {directory}")
    solara.Info(f"You selected path: {selected}")
    solara.Info(f"You opened file: {opened}")

    if can_select.value:
        solara.Button(label="Select random file", on_click=select_random_file)


__doc__ += apidoc(solara.FileBrowser.f)  # type: ignore
