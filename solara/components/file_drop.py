import threading
import typing
from typing import Any, Callable, List, Optional, Union, cast

import traitlets
from ipyvue import Template
from ipyvuetify.extra import FileInput
from ipywidgets import widget_serialization
from typing_extensions import TypedDict

import solara
import solara.hooks as hooks


class FileInfo(TypedDict):
    name: str
    size: int
    file_obj: typing.BinaryIO
    data: Optional[bytes]


class FileDropZone(FileInput):
    # override to narrow traitlet of FileInput
    template = traitlets.Instance(Template).tag(sync=True, **widget_serialization)
    template_file = (__file__, "file_drop.vue")
    items = traitlets.List(default_value=cast(List[Any], [])).tag(sync=True)
    label = traitlets.Unicode().tag(sync=True)
    multiple = traitlets.Bool(True).tag(sync=True)


@solara.component
def _FileDrop(
    label="Drop file(s) here",
    on_total_progress: Optional[Callable[[float], None]] = None,
    on_file: Optional[Callable[[Union[FileInfo, List[FileInfo]]], None]] = None,
    lazy: bool = True,
    multiple: bool = False,
):
    """Generic implementation used by FileDrop and FileDropMultiple.

    If multiple=True, multiple files can be uploaded.
    """

    file_info, set_file_info = solara.use_state(None)
    wired_files, set_wired_files = solara.use_state(cast(Optional[typing.List[FileInfo]], None))

    file_drop = FileDropZone.element(label=label, on_total_progress=on_total_progress, on_file_info=set_file_info, multiple=multiple)  # type: ignore

    def wire_files():
        if not file_info:
            return

        real = cast(FileDropZone, solara.get_widget(file_drop))

        # workaround for @observe being cleared
        real.version += 1
        real.reset_stats()

        set_wired_files(cast(typing.List[FileInfo], real.get_files()))

    solara.use_effect(wire_files, [file_info])

    def handle_file(cancel: threading.Event):
        if not wired_files:
            return
        if on_file:
            for i in range(len(wired_files)):
                if not lazy:
                    wired_files[i]["data"] = wired_files[i]["file_obj"].read()
                else:
                    wired_files[i]["data"] = None
            if multiple:
                on_file(wired_files)
            else:
                on_file(wired_files[0])

    result: solara.Result = hooks.use_thread(handle_file, [wired_files])
    if result.error:
        raise result.error

    return file_drop


@solara.component
def FileDrop(
    label="Drop file here",
    on_total_progress: Optional[Callable[[float], None]] = None,
    on_file: Optional[Callable[[FileInfo], None]] = None,
    lazy: bool = True,
):
    """Region a user can drop a file into for file uploading.

    If lazy=True, no file content will be loaded into memory,
    nor will any data be transferred by default.
    If lazy=False, file content will be loaded into memory and passed to the `on_file` callback via the `FileInfo.data` attribute.


    A file object is of the following argument type:
    ```python
    class FileInfo(typing.TypedDict):
        name: str  # file name
        size: int  # file size in bytes
        file_obj: typing.BinaryIO
        data: Optional[bytes]: bytes  # only present if lazy=False
    ```


    ## Arguments
     * `on_total_progress`: Will be called with the progress in % of the file upload.
     * `on_file`: Will be called with a `FileInfo` object, which contains the file `.name`, `.length` and a `.file_obj` object.
     * `lazy`: Whether to load the file contents into memory or not. If `False`,
        the file contents will be loaded into memory via the `.data` attribute of file object(s).

    ## Load into Pandas
    To load the data into a Pandas DF, set `lazy=False` and use `file['file_obj']` (be careful of memory)<br>
    You can run this directly in your Jupyter notebook

    ```python
    import io
    import pandas as pd
    import solara

    @solara.component
    def Page():
        def load_file_df(file):
            df = pd.read_csv(file["file_obj"])
            print("Loaded dataframe:")
            print(df)

        solara.FileDrop(label="Drop file to see dataframe!", on_file=load_file_df)

    ```

    """

    return _FileDrop(label=label, on_total_progress=on_total_progress, on_file=on_file, lazy=lazy, multiple=False)


@solara.component
def FileDropMultiple(
    label="Drop files here",
    on_total_progress: Optional[Callable[[float], None]] = None,
    on_file: Optional[Callable[[List[FileInfo]], None]] = None,
    lazy: bool = True,
):
    """Region a user can drop multiple files into for file uploading.

    Almost identical to `FileDrop` except that multiple files can be dropped and `on_file` is called
    with a list of `FileInfo` objects.

    ## Arguments
     * `on_total_progress`: Will be called with the progress in % of the file(s) upload.
     * `on_file`: Will be called with a `List[FileInfo]`.
        Each `FileInfo` contains the file `.name`, `.length`, `.file_obj` object, and `.data` attributes.
     * `lazy`: Whether to load the file contents into memory or not.

    """

    return _FileDrop(label=label, on_total_progress=on_total_progress, on_file=on_file, lazy=lazy, multiple=True)
