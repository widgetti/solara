from pathlib import Path

from solara.website.components.markdown import MarkdownWithMetadata
from solara.website.components.sidebar import Sidebar


title = "Roadmap"
HERE = Path(__file__)
Sidebar = Sidebar

Page = MarkdownWithMetadata(Path(HERE.parent / "roadmap.md").read_text())
