"""
# FileDrop components

FileDrop comes in two flavours:

   * `FileDrop` for a single file upload
   * `FileDropMultiple` which allows for multiple file upload


"""

import textwrap
from typing import List, cast

import solara
from solara.components.file_drop import FileInfo
from solara.website.utils import apidoc


@solara.component
def FileDropMultipleDemo():
    content, set_content = solara.use_state(cast(List[bytes], []))
    filename, set_filename = solara.use_state(cast(List[str], []))
    size, set_size = solara.use_state(cast(List[int], []))

    def on_file(files: List[FileInfo]):
        set_filename([f["name"] for f in files])
        set_size([f["size"] for f in files])
        set_content([f["file_obj"].read(100) for f in files])

    solara.FileDropMultiple(
        label="Drag and drop files(s) here to read the first 100 bytes.",
        on_file=on_file,
        lazy=True,  # We will only read the first 100 bytes
    )
    if content:
        solara.Info(f"Number of uploaded files: {len(filename)}")
        for f, s, c in zip(filename, size, content):
            solara.Info(f"File {f} has total length: {s}\n, first 100 bytes:")
            solara.Preformatted("\n".join(textwrap.wrap(repr(c))))


@solara.component
def FileDropDemo():
    content, set_content = solara.use_state(b"")
    filename, set_filename = solara.use_state("")
    size, set_size = solara.use_state(0)

    def on_file(f: FileInfo):
        set_filename(f["name"])
        set_size(f["size"])
        set_content(f["file_obj"].read(100))

    solara.FileDrop(
        label="Drag and drop a file here to read the first 100 bytes.",
        on_file=on_file,
        lazy=True,  # We will only read the first 100 bytes
    )
    if content:
        solara.Info(f"File {filename} has total length: {size}\n, first 100 bytes:")
        solara.Preformatted("\n".join(textwrap.wrap(repr(content))))


@solara.component
def Page():
    with solara.Row():
        with solara.Card(title="FileDrop"):
            FileDropDemo()
        with solara.Card(title="FileDropMultiple"):
            FileDropMultipleDemo()


__doc__ += "# FileDrop"
__doc__ += apidoc(solara.FileDrop.f)  # type: ignore
__doc__ += "# FileDropMultiple"
__doc__ += apidoc(solara.FileDropMultiple.f)  # type: ignore
