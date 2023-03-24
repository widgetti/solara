"""
FileInput component.
"""


from typing import Callable, List, Optional, Union, cast

from ipyvuetify.extra import FileInput as ExtraFileInput

import solara
import solara.hooks as hooks
from solara.components.file_drop import FileInfo


@solara.component
def FileInput(
    label: str = "",
    on_total_progress: Optional[Callable[[float], None]] = None,
    on_file: Union[None, Callable[[Optional[FileInfo]], None], Callable[[List[FileInfo]], None]] = None,
    accept: str = "",
    multiple: bool = False,
    lazy: bool = True,
    **kwargs
):
    """A file input widget the user can click on and select one or multiple files for uploading.

     If lazy=True, no file content will be loaded into memory,
    nor will any data be transferred by default.
    A list of file objects is passed to the `on_file` callback, and data will be transferred
    when needed.

    If lazy=False, the file content will be loaded into memory and passed to the `on_file` callback via the `.data`
    attribute on the file objects.

    The on_file callback takes List[FileInfo] as an argument, where FileInfo is the following type:
    ```python
    class FileInfo(typing.TypedDict):
        name: str  # file name
        size: int  # file size in bytes
        file_obj: typing.BinaryIO
        data: Optional[bytes]: bytes  # only present if lazy=False
    ```

     ## Arguments
     * `on_total_progress`: Will be called with the progress in % of the file upload.
     * `on_file`: Will be called with a `List[FileInfo]` object, which contain the file `.name`, `.length` and a `.file_obj` objects.
     * `accept`: A comma-separated list of unique file type specifiers.
     * `multiple`: Whether to allow multiple files to be selected.
     * `lazy`: Whether to load the file content into memory or not. If `False`,
        the file content will be loaded into memory and passed to the `on_file` callback via the `.data` attribute.
     * `**kwargs`: Additional keyword arguments to pass to the underlying `FileInput` widget.


    """

    file_info, set_file_info = solara.use_state(None)
    wired_files, set_wired_files = solara.use_state(cast(List[FileInfo], []))

    file_input = ExtraFileInput.element(
        label=label, on_total_progress=on_total_progress, on_file_info=set_file_info, accept=accept, multiple=multiple, **kwargs
    )

    def wire_files() -> None:
        if not file_info:
            set_wired_files([])

        real = cast(ExtraFileInput, solara.get_widget(file_input))

        # workaround for @observe being cleared
        real.version += 1
        real.reset_stats()

        set_wired_files(cast(List[FileInfo], real.get_files()))

    solara.use_effect(wire_files, [file_info])

    def handle_file() -> None:
        if not on_file:
            return
        if not wired_files:
            if multiple:
                on_file([])
            else:
                on_file(None)
            return
            # on_file([] if multiple else None)
        if lazy:
            for f_info in wired_files:
                f_info["data"] = None
        else:
            for f_info in wired_files:
                f_info["data"] = f_info["file_obj"].read()

        if multiple:
            on_file(wired_files)
        else:
            on_file(wired_files[0])

    result: solara.Result = hooks.use_thread(handle_file, [wired_files])
    if result.error:
        raise result.error

    return file_input
