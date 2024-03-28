from pathlib import Path

import solara
from solara.website.components.markdown import MarkdownWithMetadata

title = "FAQ"
HERE = Path(__file__)


@solara.component
def Page(route_external=None):
    MarkdownWithMetadata(Path(HERE.parent / "content" / "99-faq.md").read_text())
