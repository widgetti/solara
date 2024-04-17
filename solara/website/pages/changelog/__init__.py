from pathlib import Path

import solara
from solara.website.components.sidebar import Sidebar

title = "Changelog"
HERE = Path(__file__)

Page = solara.Markdown(Path(HERE.parent / "changelog.md").read_text())
Sidebar = Sidebar
