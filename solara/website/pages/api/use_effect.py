from pathlib import Path
from . import NoPage

HERE = Path(__file__).parent
__doc__ = open(HERE / "use_effect.md").read()

Page = NoPage
title = "use_effect"
