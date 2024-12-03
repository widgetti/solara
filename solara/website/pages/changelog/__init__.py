from pathlib import Path

from solara.website.components.sidebar import Sidebar
from solara.website.components import MarkdownWithMetadata

title = "Changelog"
HERE = Path(__file__)

Page = MarkdownWithMetadata(Path(HERE.parent / "changelog.md").read_text())
Sidebar = Sidebar
