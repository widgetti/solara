from pathlib import Path

from solara.autorouting import generate_routes_directory

title = "Docs"
HERE = Path(__file__)
# if we didn't put the content in the subdirectory, but pointed to the current file
# we would include the current file recursively, causing an infinite loop
routes = generate_routes_directory(HERE.parent / "content")
