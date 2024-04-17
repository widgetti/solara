from pathlib import Path

import solara
from solara.website.components.sidebar import Sidebar

title = "Contact"
HERE = Path(__file__)

Page = solara.Markdown(Path(HERE.parent / "contact.md").read_text())
Sidebar = Sidebar
