from pathlib import Path

from solara.autorouting import generate_routes_directory
from solara.website.components.markdown import MarkdownWithMetadata

HERE = Path(__file__)
# if we didn't put the content in the subdirectory, but pointed to the current file
# we would include the current file recursively, causing an infinite loop
routes = generate_routes_directory(HERE.parent / "content", MarkdownWithMetadata)
