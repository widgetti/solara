from pathlib import Path
from . import NoPage

HERE = Path(__file__).parent
__doc__ = open(HERE / "use_memo.md").read()

Page = NoPage
title = "use_memo"
