from pathlib import Path

import solara

title = "FAQ"
HERE = Path(__file__)


@solara.component
def Page(route_external=None):
    solara.Markdown(Path(HERE.parent / "content" / "99-faq.md").read_text())
