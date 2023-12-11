from pathlib import Path

import solara

title = "Contact"
HERE = Path(__file__)

Page = solara.Markdown(Path(HERE.parent / "contact.md").read_text())
