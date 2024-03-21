from pathlib import Path

import solara

title = "Changelog"
HERE = Path(__file__)

Page = solara.Markdown(Path(HERE.parent / "changelog.md").read_text())
