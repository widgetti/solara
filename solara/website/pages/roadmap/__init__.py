from pathlib import Path

from solara.website.components.markdown import MarkdownWithMetadata


title = "Roadmap"
HERE = Path(__file__)

Page = MarkdownWithMetadata(Path(HERE.parent / "roadmap.md").read_text())
