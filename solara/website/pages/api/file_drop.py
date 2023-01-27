"""
# FileDrop
"""
import textwrap

import solara
from solara.components.file_drop import FileInfo
from solara.website.utils import apidoc


@solara.component
def Page():
    content, set_content = solara.use_state(b"")
    filename, set_filename = solara.use_state("")
    size, set_size = solara.use_state(0)

    def on_file(file: FileInfo):
        set_filename(file["name"])
        set_size(file["size"])
        f = file["file_obj"]
        set_content(f.read(100))

    with solara.Div() as main:
        solara.FileDrop(
            label="Drag and drop a file here to read the first 100 bytes",
            on_file=on_file,
            lazy=True,  # We will only read the first 100 bytes
        )
        if content:
            solara.Info(f"File {filename} has total length: {size}\n, first 100 bytes:")
            solara.Preformatted("\n".join(textwrap.wrap(repr(content))))

    return main


__doc__ += apidoc(solara.FileDrop.f)  # type: ignore
