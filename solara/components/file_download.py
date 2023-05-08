from pathlib import Path
from typing import BinaryIO, Callable, Optional, Union, cast

import ipyvuetify as vy
import ipywidgets as widgets
import traitlets

import solara


class FileDownloadWidget(vy.VuetifyTemplate):
    template_file = (__file__, "download.vue")
    children = traitlets.List().tag(sync=True, **widgets.widget_serialization)
    filename = traitlets.Unicode().tag(sync=True)
    bytes = traitlets.Bytes(None, allow_none=True).tag(sync=True)
    mime_type = traitlets.Unicode("application/octet-stream").tag(sync=True)
    request_download = traitlets.Bool(False).tag(sync=True)


@solara.component
def FileDownload(
    data: Union[str, bytes, BinaryIO, Callable[[], Union[str, bytes, BinaryIO]]],
    filename: Optional[str] = None,
    label: Optional[str] = None,
    icon_name: Optional[str] = "mdi-cloud-download-outline",
    close_file: bool = True,
    mime_type: str = "application/octet-stream",
    string_encoding: str = "utf-8",
    children=[],
):
    """Download a file or data.

    ## Simple usage

    By default, if no children are provided, a button is created with the label "Download: {filename}".

    ```solara
    import solara

    data = "This is the content of the file"

    @solara.component
    def Page():
        solara.FileDownload(data, filename="solara-download.txt", label="Download file")
    ```

    ## Advanced usage

    If children are provided, they are displayed instead of the button. The children can be any solara component,
    including a button, markdown text, or an image.

    ```solara
    import solara

    data = "This is the content of the file"

    @solara.component
    def Page():
        with solara.FileDownload(data, "solara-download-2.txt"):
            solara.Markdown("Any text, or even an image")
            solara.Image("https://solara.dev/static/public/beach.jpeg", width="200px")
    ```

    ## Custom button

    If children are provided, they are displayed instead of the button. The children can be any solara component,
    including a button, markdown text, or an image.

    ```solara
    import solara

    data = "This is the content of the file"

    @solara.component
    def Page():
        with solara.FileDownload(data, "solara-download-2.txt"):
            solara.Button("Custom download button", icon_name="mdi-cloud-download-outline", color="primary")
    ```

    ## Usage with file

    A file object can be used as data. The file will be closed after downloading by default.

    ```solara
    import solara
    import pandas as pd

    df = pd.DataFrame({"id": [1, 2, 3], "name": ["John", "Mary", "Bob"]})

    @solara.component
    def Page():
        file_object = df.to_csv(index=False)
        solara.FileDownload(file_object, "users.csv", mime_type="application/vnd.ms-excel")
    ```

    If a file like object is used, we try to base the filename on the file object.
    ```solara
    import solara
    import solara.website.pages
    import os

    filename = os.path.dirname(solara.website.__file__) + "/public/beach.jpeg"

    @solara.component
    def Page():
        # only open the file once by using use_memo
        file_object = solara.use_memo(lambda: open(filename, "rb"), [])
        # no filename is provided, but we can extract it from the file object
        solara.FileDownload(file_object, mime_type="image/jpeg", close_file=False)
    ```

    ## Lazy reading

    Not only is the data lazily uploaded to the browser, but also the data is only read when the download is requested.
    This happens for files by default, but can also be used by passing in a callback function.

    ```solara
    import solara
    import time

    @solara.component
    def Page():
        def get_data():
            # I run in a thread, so I can do some heavy processing
            time.sleep(3)
            # I only get called when the download is requested
            return "This is the content of the file"
        solara.FileDownload(get_data, "solara-lazy-download.txt")
    ```

    ## Arguments

     * `data`: The data to download. Can be a string, bytes, or a file like object, or a function that returns one of these.
     * `filename`: The name of the file the user will see as default when downloading (default name is "solara-download.dat").
        If a file object is provided, the filename will be extracted from the file object if possible.
     * `label`: The label of the button. If not provided, the label will be "Download: {filename}".
     - `icon_name`: The name of the icon to display on the button ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
     * `close_file`: If a file object is provided, close the file after downloading (default True).
     * `mime_type`: The mime type of the file. If not provided, the mime type will be "application/octet-stream",
           For instance setting it to "application/vnd.ms-excel" will allow the user OS to directly open the
           file into Excel.
     * `string_encoding`: The encoding to use when converting a string to bytes (default "utf-8").

    ## Note on file size

    Note that the data will be kept in memory when downloading.
    If the file is large (>10 MB), and when using [Solara server](/docs/understanding), we recommend using the
    [static files directory](/docs/reference/static-files) instead.

    """
    request_download, set_request_download = solara.use_state(False)

    # if the data changes, we 'reset'
    def reset():
        nonlocal request_download
        request_download = False
        set_request_download(False)

    solara.use_memo(reset, [data])

    # we only upload to the frontend if clicked
    def get_data() -> Optional[bytes]:
        if request_download:
            if callable(data):
                data_non_lazy = data()
            else:
                data_non_lazy = data
            if hasattr(data_non_lazy, "read"):
                if hasattr(data_non_lazy, "seek"):
                    if hasattr(data_non_lazy, "tell") and data_non_lazy.tell() != 0:
                        data_non_lazy.seek(0)
                content = data_non_lazy.read()  # type: ignore
                if close_file:
                    data_non_lazy.close()  # type: ignore
                return content
            elif isinstance(data_non_lazy, str):
                return data_non_lazy.encode(string_encoding)
            else:
                return cast(bytes, data_non_lazy)
        return None

    bytes_result: solara.Result[Optional[bytes]] = solara.use_thread(get_data, dependencies=[request_download, data])
    if filename is None and hasattr(data, "name"):
        try:
            filename = Path(data.name).name  # type: ignore
        except Exception:
            pass
    filename = filename or "solara-download.dat"
    label = label or ("Download: " + filename)
    FileDownloadWidget.element(
        filename=filename,
        bytes=bytes_result.value if bytes_result.state == solara.ResultState.FINISHED else None,
        request_download=request_download,
        on_request_download=set_request_download,
        children=children or [solara.Button(label, loading=bytes_result.state == solara.ResultState.RUNNING, icon_name=icon_name)],
        mime_type=mime_type,
    )
    if bytes_result.state == solara.ResultState.ERROR and bytes_result.error:
        raise bytes_result.error
