import sys
from typing import Dict

from rich import print

warned: Dict[str, bool] = {}


def check(name):
    if name in warned:
        return
    warned[name] = True
    print(  # noqa: T201
        f"[bold yellow]Using the {name} feature requires a license, unless used for non-commerical use."
        "Please contact us at contact@solara.dev to get a license.",
        file=sys.stderr,
    )
