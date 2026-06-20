import asyncio
import logging
import os
from dataclasses import dataclass
from os.path import isfile, join
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union, cast

import humanize
import ipyvuetify as vy
import traitlets

try:
    import watchfiles
except ModuleNotFoundError:
    watchfiles = None  # type: ignore

import solara
from solara.components import Div

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _FileBrowserEntry(Generic[T]):
    name: str
    value: T
    is_file: bool
    size: Optional[str] = None


class _FileBrowserSource(Generic[T]):
    def list(self, location: T) -> List[_FileBrowserEntry[T]]:
        raise NotImplementedError

    def parent(self, location: T) -> Optional[T]:
        raise NotImplementedError

    def can_read(self, location: T) -> bool:
        return True

    def location_name(self, location: T) -> str:
        return str(location)

    def value_name(self, value: T) -> str:
        return str(value)

    def is_visible(self, location: T, value: T) -> bool:
        return any(entry.value == value for entry in self.list(location))

    def sync_location_from_value(self, value: T) -> Optional[T]:
        return None

    def watch(self, location: T, refresh: Callable[[], None]) -> Optional[Callable[[], None]]:
        return None


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
    click_event = traitlets.Dict(allow_none=True, default_value=None).tag(sync=True)
    double_click_event = traitlets.Dict(allow_none=True, default_value=None).tag(sync=True)
    selected_names = traitlets.List(cast(List[str], [])).tag(sync=True)
    use_selected_names = traitlets.Bool(False).tag(sync=True)
    scroll_pos = traitlets.Int(allow_none=True).tag(sync=True)

    def test_click(self, path: Union[Path, str], double_click=False):
        """Simulate a click or double click at the Python side"""
        matches = [k for k in self.files if k["name"] == str(path)]
        if len(matches) == 0:
            names = [k["name"] for k in self.files]
            raise NameError(f"Could not find {path}, possible filenames: {names}")
        item = {"name": matches[0]["name"], "is_file": matches[0]["is_file"]}
        event = dict(item)
        self._test_click_counter = getattr(self, "_test_click_counter", 0) + 1
        event["_click_id"] = self._test_click_counter
        if double_click:
            self.double_clicked = item
            self.double_click_event = event
        else:
            self.clicked = item
            self.click_event = event

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


def _validate_selection_list(paths: List[T], validate: Optional[Callable[[List[T]], None]] = None) -> None:
    if validate:
        validate(paths)


def _FileBrowserBase(
    source: _FileBrowserSource[T],
    location: Union[T, solara.Reactive[T]],
    selected: Union[None, T, solara.Reactive[Optional[T]]] = None,
    selected_multiple: Union[None, List[T], solara.Reactive[List[T]]] = None,
    on_location_change: Optional[Callable[[T], None]] = None,
    on_select: Optional[Callable[[Optional[T]], None]] = None,
    on_select_multiple: Optional[Callable[[List[T]], None]] = None,
    on_open: Optional[Callable[[T], None]] = None,
    selection_mode: str = "open",
    validate_multiple: Optional[Callable[[List[T]], None]] = None,
    watch_key: Any = None,
    on_select_name: str = "on_select",
):
    if selection_mode not in {"open", "single", "multiple"}:
        raise ValueError("selection_mode must be 'open', 'single', or 'multiple'")

    current_location = solara.use_reactive(location)
    double_clicked, set_double_clicked = solara.use_state(cast(Optional[Dict[str, Any]], None))
    warning, set_warning = solara.use_state(cast(Optional[str], None))
    scroll_pos_stack, set_scroll_pos_stack = solara.use_state(cast(List[int], []))
    scroll_pos, set_scroll_pos = solara.use_state(0)
    file_change_counter, set_file_change_counter = solara.use_state(0)
    del file_change_counter
    selected_private, set_selected_private = use_reactive_or_value(
        selected,
        on_value=on_select if selection_mode == "single" else lambda x: None,
        value_name="selected",
        on_value_name=on_select_name,
        use_internal_value=selection_mode != "single",
    )

    if selection_mode == "multiple":
        selected_multiple_internal, set_selected_multiple_internal = solara.use_state(cast(List[T], []))
        if selected_multiple is None:
            selected_multiple_private = selected_multiple_internal

            def set_selected_multiple_private(values: List[T]):
                values = list(values)
                _validate_selection_list(values, validate_multiple)
                set_selected_multiple_internal(values)
                if on_select_multiple:
                    on_select_multiple(values)

        else:
            selected_multiple_reactive = solara.use_reactive(selected_multiple, on_select_multiple)
            selected_multiple_private = selected_multiple_reactive.value

            def set_selected_multiple_private(values: List[T]):
                values = list(values)
                _validate_selection_list(values, validate_multiple)
                selected_multiple_reactive.set(values)

        _validate_selection_list(selected_multiple_private, validate_multiple)
    else:
        selected_multiple_private = cast(List[T], [])

        def set_selected_multiple_private(values: List[T]):
            pass

    del selected, selected_multiple

    def sync_location_from_selected():
        if selection_mode == "single" and selected_private is not None:
            current_parent = source.parent(current_location.value)
            if current_parent is not None and selected_private == current_parent:
                return
            new_location = source.sync_location_from_value(cast(T, selected_private))
            if new_location is not None:
                current_location.value = new_location

    solara.use_effect(sync_location_from_selected, [selected_private])

    def watch_location():
        return source.watch(current_location.value, lambda: set_file_change_counter(lambda value: value + 1))

    solara.use_effect(watch_location, [current_location.value, watch_key])

    def change_location(new_location: T):
        if source.can_read(new_location):
            current_location.value = new_location
            if on_location_change:
                on_location_change(new_location)
            set_warning(None)
            return True
        else:
            set_warning(f"[no read access to {source.location_name(new_location)}]")
            return False

    def clear_multiple_selection():
        if selected_multiple_private:
            set_selected_multiple_private([])

    def toggle_value(value: T):
        values = list(selected_multiple_private)
        if value in values:
            values = [existing for existing in values if existing != value]
        else:
            values.append(value)
        set_selected_multiple_private(values)

    entries = source.list(current_location.value)
    entry_by_name = {entry.name: entry for entry in entries}
    parent = source.parent(current_location.value)

    def on_item(item, double_click):
        if item is None:
            if selection_mode == "multiple":
                clear_multiple_selection()
                return
            if selection_mode == "single" and on_select:
                on_select(None)
            return
        if item["name"] == "..":
            if parent is None:
                return
            if selection_mode == "multiple":
                if double_click and change_location(parent):
                    if scroll_pos_stack:
                        last_pos = scroll_pos_stack[-1]
                        set_scroll_pos_stack(scroll_pos_stack[:-1])
                        set_scroll_pos(last_pos)
                    clear_multiple_selection()
                    set_double_clicked(None)
                return
            action_change_location = (selection_mode == "single" and double_click) or (selection_mode == "open" and not double_click)
            if action_change_location and change_location(parent):
                if scroll_pos_stack:
                    last_pos = scroll_pos_stack[-1]
                    set_scroll_pos_stack(scroll_pos_stack[:-1])
                    set_scroll_pos(last_pos)
                set_selected_private(None)
                set_double_clicked(None)
                if selection_mode == "single" and on_select:
                    on_select(None)
            if selection_mode == "single" and not double_click:
                if on_select:
                    on_select(parent)
            return

        entry = entry_by_name[item["name"]]
        if selection_mode == "multiple":
            if double_click:
                if entry.is_file:
                    if on_open:
                        on_open(entry.value)
                else:
                    if change_location(entry.value):
                        set_scroll_pos_stack(scroll_pos_stack + [scroll_pos])
                        set_scroll_pos(0)
                clear_multiple_selection()
                set_double_clicked(None)
            else:
                toggle_value(entry.value)
            return
        if (selection_mode == "single" and double_click) or (selection_mode == "open" and not double_click):
            if entry.is_file:
                if on_open:
                    on_open(entry.value)
            else:
                if change_location(entry.value):
                    set_scroll_pos_stack(scroll_pos_stack + [scroll_pos])
                    set_scroll_pos(0)
                set_selected_private(None)
            set_double_clicked(None)
            if selection_mode == "single" and on_select:
                on_select(None)
        elif selection_mode == "single" and not double_click:
            if on_select:
                on_select(entry.value)
        else:  # open mode double click is ignored
            raise RuntimeError("Combination should not happen")  # pragma: no cover

    def on_click(item):
        if selection_mode == "single":
            set_selected_private(item["name"] if item else None)
        elif selection_mode == "open":
            set_selected_private(item["name"] if item and item["is_file"] else None)
        on_item(item, False)

    def on_clicked_change(item):
        if item is None:
            on_click(None)

    def on_double_click(item):
        if item is not None:
            set_double_clicked({"name": item["name"], "is_file": item["is_file"]})
        if selection_mode in {"single", "multiple"}:
            on_item(item, True)

    files = ([{"name": "..", "is_file": False, "size": None}] if parent is not None else []) + [
        {"name": entry.name, "is_file": entry.is_file, "size": entry.size} for entry in entries
    ]
    clicked = None
    if selected_private is not None:
        name = selected_private if isinstance(selected_private, str) else source.value_name(cast(T, selected_private))
        clicked = {"name": name, "is_file": not isinstance(selected_private, str), "size": None}
    selected_names = []
    if selection_mode == "multiple":
        selected_names = [source.value_name(value) for value in selected_multiple_private if source.is_visible(current_location.value, value)]

    with Div(class_="solara-file-browser") as main:
        Div(children=[source.location_name(current_location.value)])
        file_list_kwargs: Dict[str, Any] = dict(
            files=files,
            clicked=None if selection_mode == "multiple" else clicked,
            on_clicked=on_clicked_change,
            on_click_event=on_click,
            double_clicked=double_clicked,
            on_double_click_event=on_double_click,
            scroll_pos=scroll_pos,
            on_scroll_pos=set_scroll_pos,
        )
        if selection_mode == "multiple":
            file_list_kwargs.update(selected_names=selected_names, use_selected_names=True)
        FileListWidget.element(**file_list_kwargs).key("FileList")
        if warning:
            Div(style_="font-weight: bold; color: red", children=[warning])

    return main


def _validate_path_list(paths: List[Path], name: str = "selected") -> None:
    for path in paths:
        if not isinstance(path, Path):
            raise TypeError(f"{name} must contain pathlib.Path instances")


class _LocalFileBrowserSource(_FileBrowserSource[Path]):
    def __init__(self, filter: Callable[[Path], bool], directory_first: bool, watch: bool):
        self.filter = filter
        self.directory_first = directory_first
        self.watch_enabled = watch

    def list(self, location: Path) -> List[_FileBrowserEntry[Path]]:
        return [
            _FileBrowserEntry(
                name=item["name"],
                value=location / item["name"],
                is_file=item["is_file"],
                size=item["size"],
            )
            for item in list_dir(location, filter=self.filter, directory_first=self.directory_first)
        ]

    def parent(self, location: Path) -> Path:
        if location.is_symlink():
            return location.parent
        elif any([d.is_symlink() for d in location.parents]):
            return location.parent
        else:
            return location.resolve().parent

    def can_read(self, location: Path) -> bool:
        return os.access(location, os.R_OK)

    def location_name(self, location: Path) -> str:
        return str(location.resolve())

    def value_name(self, value: Path) -> str:
        return value.name

    def is_visible(self, location: Path, value: Path) -> bool:
        if not isinstance(value, Path):
            return False
        if value.parent == location:
            return True
        return value.is_absolute() and value.parent.resolve() == location.resolve()

    def sync_location_from_value(self, value: Path) -> Optional[Path]:
        if isinstance(value, Path) and value.is_absolute():
            return value.parent.resolve()
        return None

    def watch(self, location: Path, refresh: Callable[[], None]) -> Optional[Callable[[], None]]:
        if not self.watch_enabled:
            return None
        if not watchfiles:
            logger.warning("watchfiles not installed, cannot watch directory")
            return None

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No running event loop, cannot watch directory for changes")
            return None

        async def watch_task():
            try:
                async for _ in watchfiles.awatch(location):
                    logger.debug("Directory %s changed, refreshing file list", location)
                    refresh()
            except RuntimeError:
                pass  # swallow the RuntimeError: Already borrowed errors from watchfiles
            except Exception:
                logger.exception("Error watching directory")

        future = asyncio.create_task(watch_task())

        def cancel():
            future.cancel()

        return cancel


def _FileBrowserLocal(
    directory: Union[None, str, Path, solara.Reactive[Path]] = None,
    selected: Union[None, Path, solara.Reactive[Optional[Path]]] = None,
    selected_paths: Union[None, List[Path], solara.Reactive[List[Path]]] = None,
    on_directory_change: Optional[Callable[[Path], None]] = None,
    on_path_select: Optional[Callable[[Optional[Path]], None]] = None,
    on_paths_select: Optional[Callable[[List[Path]], None]] = None,
    on_file_open: Optional[Callable[[Path], None]] = None,
    filter: Callable[[Path], bool] = lambda x: True,
    directory_first: bool = False,
    on_file_name: Optional[Callable[[str], None]] = None,
    start_directory=None,
    can_select=False,
    watch: bool = False,
    multiple: bool = False,
    allow_directory_string: bool = True,
):
    """Local filesystem implementation shared by FileBrowser variants."""
    if start_directory is not None:
        directory = start_directory  # pragma: no cover
    if directory is None:
        directory = Path(os.getcwd())  # pragma: no cover
    if isinstance(directory, str):
        if not allow_directory_string:
            raise TypeError("directory must be a pathlib.Path or solara.Reactive[Path]")
        directory = Path(directory)
    if not allow_directory_string and isinstance(directory, solara.Reactive) and isinstance(directory.value, str):
        raise TypeError("directory must be a pathlib.Path or solara.Reactive[Path]")

    if multiple:
        if isinstance(selected_paths, solara.Reactive):
            _validate_path_list(selected_paths.value)
        elif selected_paths is not None:
            _validate_path_list(selected_paths)

    source = _LocalFileBrowserSource(filter=filter, directory_first=directory_first, watch=watch)
    selection_mode = "multiple" if multiple else "single" if can_select else "open"

    def on_open(path: Path):
        if on_file_open:
            on_file_open(path)
        if on_file_name is not None:
            on_file_name(str(path))

    return _FileBrowserBase(
        source,
        directory,
        selected,
        selected_multiple=selected_paths,
        on_location_change=on_directory_change,
        on_select=on_path_select,
        on_select_multiple=on_paths_select,
        on_open=on_open,
        selection_mode=selection_mode,
        validate_multiple=_validate_path_list,
        watch_key=watch,
        on_select_name="on_path_select",
    )


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
    watch: bool = False,
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
     * `watch`: If `True`, watch the current directory for file changes and automatically refresh the file list.
        Requires the `watchfiles` package to be installed.
    """
    return _FileBrowserLocal(
        directory=directory,
        selected=selected,
        on_directory_change=on_directory_change,
        on_path_select=on_path_select,
        on_file_open=on_file_open,
        filter=filter,
        directory_first=directory_first,
        on_file_name=on_file_name,
        start_directory=start_directory,
        can_select=can_select,
        watch=watch,
    )


@solara.component
def FileBrowserMultiple(
    directory: Union[None, Path, solara.Reactive[Path]] = None,
    selected: Union[None, List[Path], solara.Reactive[List[Path]]] = None,
    on_paths_select: Optional[Callable[[List[Path]], None]] = None,
    on_directory_change: Optional[Callable[[Path], None]] = None,
    on_file_open: Optional[Callable[[Path], None]] = None,
    filter: Callable[[Path], bool] = lambda x: True,
    directory_first: bool = False,
    watch: bool = False,
):
    """File/directory browser that supports selecting multiple local paths.

    Selection values are always `pathlib.Path` instances. Unlike `FileBrowser`,
    this component does not accept string directories.

    Single-clicking a file or directory toggles it in the selected path list.
    Double-clicking a file opens it, and double-clicking a directory navigates
    into it. Opening or navigating clears the current selection.

    ## Arguments

     * `directory`: The directory to start in. If `None`, the current working directory is used.
     * `selected`: The selected files or directories. If `None`, no path is selected.
     * `on_paths_select`: Callback called with the selected path list.
     * `on_directory_change`: Called when double-clicking a directory.
     * `on_file_open`: Called when double-clicking a file.
     * `filter`: A function that takes a `Path` and returns `True` if the file/directory should be shown.
     * `directory_first`: If `True` directories are shown before files. Default: `False`.
     * `watch`: If `True`, watch the current directory for file changes and automatically refresh the file list.
        Requires the `watchfiles` package to be installed.
    """
    return _FileBrowserLocal(
        directory=directory,
        selected_paths=selected,
        on_paths_select=on_paths_select,
        on_directory_change=on_directory_change,
        on_file_open=on_file_open,
        filter=filter,
        directory_first=directory_first,
        watch=watch,
        multiple=True,
        allow_directory_string=False,
    )
