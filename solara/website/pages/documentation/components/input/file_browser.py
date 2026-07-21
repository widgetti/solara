"""
# FileBrowser components

FileBrowser components browse files and directories on the server side.

   * `FileBrowser` opens files and can optionally select one path.
   * `FileBrowserMultiple` selects multiple paths.

Both components use `pathlib.Path` values for selection callbacks.
`FileBrowser` keeps string directory support for backwards compatibility.
`FileBrowserMultiple` only accepts `Path` directory and selection values.
"""

import tempfile
from pathlib import Path
from typing import List, cast

import solara
from solara.website.utils import apidoc

selected_multiple = solara.reactive(cast(List[Path], []))


def create_demo_directory():
    directory = Path(tempfile.gettempdir()) / "solara-file-browser-multiple-demo"
    (directory / "reports").mkdir(parents=True, exist_ok=True)
    (directory / "notebooks").mkdir(parents=True, exist_ok=True)
    (directory / "notes.txt").write_text("notes\n")
    (directory / "report.csv").write_text("name,value\nA,1\n")
    (directory / "notebooks" / "example.ipynb").write_text("{}\n")
    return directory


@solara.component
def Page():
    directory = solara.use_memo(create_demo_directory, [])
    solara.Markdown(
        """
        `FileBrowserMultiple` selects multiple paths. The selected values are
        `pathlib.Path` objects.
        """
    )
    solara.Markdown("## FileBrowserMultiple")
    solara.FileBrowserMultiple(directory, selected=selected_multiple)

    selected_paths = selected_multiple.value
    selected_text = "\n".join(f"- `{path.relative_to(directory)}`" for path in selected_paths) or "- none"
    with solara.Div(style_="min-height: 96px"):
        solara.Markdown(f"Selected paths:\n\n{selected_text}")


__doc__ += apidoc(solara.FileBrowser.f)  # type: ignore
__doc__ += "# FileBrowserMultiple"
__doc__ += apidoc(solara.FileBrowserMultiple.f)  # type: ignore
