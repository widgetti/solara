from pathlib import Path

from solara.website.components.markdown import MarkdownWithMetadata


title = "About Us"
HERE = Path(__file__)

Page = MarkdownWithMetadata(Path(HERE.parent / "about.md").read_text())
