from pathlib import Path

from solara.website.components import NoPage

HERE = Path(__file__).parent
__doc__ = open(HERE / "use_effect.md").read()

Page = NoPage
title = "use_effect"
