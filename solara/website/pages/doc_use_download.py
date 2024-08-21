# flake8: noqa
import solara
import solara as sol
from solara.alias import rv, rw

from .docutils import IncludeComponent

file_path = "yolov3.weights"
url = "https://pjreddie.com/media/files/yolov3.weights"
expected_size = 248007048


@solara.component
def DownloadFile(file_path=file_path, url=url, expected_size=expected_size, on_done=None):
    download = solara.hooks.use_download(file_path, url, expected_size=expected_size)
    downloaded_size = download.progress * expected_size
    if on_done:
        on_done(download.progress == 1)
    if download.value:
        status = "Done 🎉"
    else:
        MEGABYTES = 2.0**20.0
        status = "Downloading {}... ({:6.2f}/{:6.2f} MB)".format(file_path, downloaded_size / MEGABYTES, expected_size / MEGABYTES)
    # status = "hi"
    # return MarkdownIt(f'{status}')
    assert download.progress is not None
    with rv.Container() as main:
        # with w.VBox() as main:
        with rv.Row():
            with rv.Col(cols=1):
                progressbar = rv.ProgressLinear(value=download.progress * 100, color="primary", striped=True, height=20)
            # with rv.Col(cols=1):
            #     MarkdownIt(f'{status}')
    return main


@solara.component
def DocUseDownload():
    with rv.Container() as main:
        with rw.VBox(layout={"padding": "20px", "max_width": "1024px"}):
            solara.MarkdownIt(
                """
# use_download

```python
def use_state(initial: T, key: str = None) -> Tuple[T, Callable[[T], T]]:
    ...
```

use_state can be used to create a variable that is local to this component, and will be preserved during rerenders.

It returns a tuple with the current value, and a setter function that should be called to change the variable. A call to this setter
will trigger a rerender, and will cause the `use_state` function to return the new value on the next render.

## Simple examples

### Click button

Lets start with a Button, that renders how many times it is clicked.
        """
            )
            IncludeComponent(
                DownloadFile,
                """
import reacton
import solara.ipywidgets as w

""",
                highlight=[6],
            )
    #             MarkdownIt("""
    # ### Markdown editor
    # Lets continue with a more typical pattern, and create new new markdown component
    #         """)
    #             IncludeComponent(MarkdownIt, md_text="# This is a custom\nMark-*down* **component**")

    #             MarkdownIt("""This component does not have state itself, the markdown text can only be set via its argument.
    # A common pattern is then to have its parent component manage the state, and pass it down:
    # """)
    #             # IncludeComponent(MarkdownEditor, md="# Edit me\nand the markdown component **will** *update*", highlight=[3,5,6])
    #             MarkdownIt("""Here we see the `MarkdownEditor` component using the `use_state` function to store the markdown text, while letting the `Textarea` component change its value""")
    return main


DownloadFile("yolov3.weights", "https://pjreddie.com/media/files/yolov3.weights", expected_size=248007048)
