import os
from os.path import isfile, join
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypeVar, Union, cast
import logging

import humanize
import ipyvuetify as vy
import traitlets

import solara
from solara.components import Div

T = TypeVar("T")
logger = logging.getLogger(__name__)


def list_dir(path, filter: Callable[[Path], bool] = lambda x: True, directory_first: bool = False) -> List[dict]:
    def mk_item(n):
        full_path = join(path, n)
        is_file = isfile(full_path)
        return {"name": n, "is_file": is_file, "size": humanize.naturalsize(os.stat(full_path).st_size) if is_file else None}

    files = [mk_item(k) for k in os.listdir(path) if not k.startswith(".") if filter(Path(path) / k)]
    sorted_files = sorted(files, key=lambda item: (item["is_file"] == directory_first, item["name"].lower()))

    return sorted_files


class FileListWidget(vy.VuetifyTemplate):
    template_file = (__file__, "file_list_widget.vue")

    files = traitlets.List(cast(List[Dict], [])).tag(sync=True)
    clicked = traitlets.Dict(allow_none=True, default_value=None).tag(sync=True)
    double_clicked = traitlets.Dict(allow_none=True, default_value=None).tag(sync=True)
    scroll_pos = traitlets.Int(allow_none=True).tag(sync=True)

    def test_click(self, path: Union[Path, str], double_click=False):
        """Simulate a click or double click at the Python side"""
        matches = [k for k in self.files if k["name"] == str(path)]
        if len(matches) == 0:
            names = [k["name"] for k in self.files]
            raise NameError(f"Could not find {path}, possible filenames: {names}")
        item = matches[0]
        if double_click:
            self.double_clicked = item
        else:
            self.clicked = item

    def __contains__(self, name):
        """Test if filename/directory name is in the current directory."""
        return name in [k["name"] for k in self.files]


def use_reactive_or_value(
    value: Union[T, solara.Reactive[T]], on_value: Optional[Callable[[T], None]] = None, value_name="value", on_value_name="on_value", use_internal_value=False
):
    def hookup_on_value():
        if isinstance(value, solara.Reactive) and on_value:
            return value.subscribe(on_value)

    solara.use_effect(hookup_on_value, [isinstance(value, solara.Reactive), on_value])
    internal_value, set_internal_value = solara.use_state(value.value if isinstance(value, solara.Reactive) else value)
    if use_internal_value:
        return internal_value, set_internal_value
    if isinstance(value, solara.Reactive):
        return value.value, value.set
    elif on_value:
        return value, on_value
    else:
        logger.warning("You should provide an %s callback if you are not using a reactive value, otherwise %s input will not update", on_value_name, value_name)
        return value, lambda x: None


@solara.component
def FileBrowser(
    directory: Union[None, str, Path, solara.Reactive[Path]] = None,
    selected: Union[None, Path, solara.Reactive[Optional[Path]]] = None,
    on_directory_change: Optional[Callable[[Path], None]] = None,
    on_path_select: Optional[Callable[[Optional[Path]], None]] = None,
    on_file_open: Optional[Callable[[Path], None]] = None,
    filter: Callable[[Path], bool] = lambda x: True,
    directory_first: bool = False,
    on_file_name: Optional[Callable[[str], None]] = None,
    start_directory=None,
    can_select=False,
):
    """File/directory browser at the server side.

    There are two modes possible

     * `can_select=False`
       * `on_file_open`: Triggered when **single** clicking a file or directory.
       * `on_path_select`: Never triggered
       * `on_directory_change`: Triggered when clicking a directory
     * `can_select=True`
       * `on_file_open`: Triggered when **double** clicking a file or directory.
       * `on_path_select`: Triggered when clicking a file or directory
       * `on_directory_change`: Triggered when double clicking a directory

    ## Arguments

     * `directory`: The directory to start in. If `None`, the current working directory is used.
     * `selected`: The selected file or directory. If `None`, no file or directory is selected (requires `can_select=True`).
     * `on_directory_change`: Depends on mode, see above.
     * `on_path_select`: Depends on mode, see above.
     * `on_file_open`: Depends on mode, see above.
     * `filter`: A function that takes a `Path` and returns `True` if the file/directory should be shown.
     * `directory_first`: If `True` directories are shown before files. Default: `False`.
     * `on_file_name`: (deprecated) Use on_file_open instead.
     * `start_directory`: (deprecated) Use directory instead.
    """
    if start_directory is not None:
        directory = start_directory  # pragma: no cover
    if directory is None:
        directory = os.getcwd()  # pragma: no cover
    if isinstance(directory, str):
        directory = Path(directory)
    # directory = directory.resolve()
    current_dir = solara.use_reactive(directory)
    double_clicked, set_double_clicked = solara.use_state(None)
    warning, set_warning = solara.use_state(cast(Optional[str], None))
    scroll_pos_stack, set_scroll_pos_stack = solara.use_state(cast(List[int], []))
    scroll_pos, set_scroll_pos = solara.use_state(0)
    selected_private, set_selected_private = use_reactive_or_value(
        selected,
        on_value=on_path_select if can_select else lambda x: None,
        value_name="selected",
        on_value_name="on_path_select",
        use_internal_value=not can_select,
    )
    # remove so we don't accidentally use it
    del selected

    def sync_directory_from_selected():
        if selected_private is not None:
            # if we select a file, we need to make sure the directory is correct
            # NOTE: although we expect a Path, abuse might make it a string
            if isinstance(selected_private, Path):
                current_dir.value = selected_private.resolve().parent

    solara.use_effect(sync_directory_from_selected, [selected_private])

    def change_dir(new_dir: Path):
        if os.access(new_dir, os.R_OK):
            current_dir.value = new_dir
            if on_directory_change:
                on_directory_change(new_dir)
            set_warning(None)
            return True
        else:
            set_warning(f"[no read access to {new_dir}]")

    def on_item(item, double_click):
        if item is None:
            if can_select and on_path_select:
                on_path_select(None)
            return
        if item["name"] == "..":
            new_dir = current_dir.value.resolve().parent
            action_change_directory = (can_select and double_click) or (not can_select and not double_click)
            if action_change_directory and change_dir(new_dir):
                if scroll_pos_stack:
                    last_pos = scroll_pos_stack[-1]
                    set_scroll_pos_stack(scroll_pos_stack[:-1])
                    set_scroll_pos(last_pos)
                set_selected_private(None)
                set_double_clicked(None)
                if on_path_select and can_select:
                    on_path_select(None)
            if can_select and not double_click:
                if on_path_select:
                    on_path_select(new_dir)
            return

        path = current_dir.value / item["name"]
        is_file = item["is_file"]
        if (can_select and double_click) or (not can_select and not double_click):
            if is_file:
                if on_file_open:
                    on_file_open(path)
                if on_file_name is not None:
                    on_file_name(str(path))
            else:
                if change_dir(path):
                    set_scroll_pos_stack(scroll_pos_stack + [scroll_pos])
                    set_scroll_pos(0)
                set_selected_private(None)
            set_double_clicked(None)
            if on_path_select and can_select:
                on_path_select(None)
        elif can_select and not double_click:
            if on_path_select:
                on_path_select(path)
        else:  # not can_select and double_click is ignored
            raise RuntimeError("Combination should not happen")  # pragma: no cover

    def on_click(item):
        set_selected_private(item["name"] if item else None)
        on_item(item, False)

    def on_double_click(item):
        set_double_clicked(item)
        if can_select:
            on_item(item, True)
        # otherwise we can ignore it, single click will handle it

    files = [{"name": "..", "is_file": False}] + list_dir(current_dir.value, filter=filter, directory_first=directory_first)
    clicked = (
        {
            "name": selected_private.name if isinstance(selected_private, Path) else selected_private,
            "is_file": isinstance(selected_private, Path),
            "size": None,
        }
        if selected_private is not None
        else None
    )
    with Div(class_="solara-file-browser") as main:
        Div(children=[str(current_dir.value.resolve())])
        FileListWidget.element(
            files=files,
            clicked=clicked,
            on_clicked=on_click,
            double_clicked=double_clicked,
            on_double_clicked=on_double_click,
            scroll_pos=scroll_pos,
            on_scroll_pos=set_scroll_pos,
        ).key("FileList")
        if warning:
            Div(style_="font-weight: bold; color: red", children=[warning])

    return main
