from pathlib import Path

import solara
from solara.autorouting import generate_routes_directory
from solara.website.components.markdown import MarkdownWithMetadata

title = "Getting Started"
HERE = Path(__file__)
# if we didn't put the content in the subdirectory, but pointed to the current file
# we would include the current file recursively, causing an infinite loop
routes = generate_routes_directory(HERE.parent / "content", MarkdownWithMetadata)


@solara.component
def Page(route_external=None):
    MarkdownWithMetadata(Path(HERE.parent / "content" / "01-introduction.md").read_text())
