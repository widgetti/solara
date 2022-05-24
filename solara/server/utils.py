import os
import traceback

from rich import print


def start_error(title, msg, exception: Exception = None):
    if exception:
        traceback.print_exception(None, exception, exception.__traceback__)
    print(f"[red]{title}:\n\t[blue]{msg}")
    os._exit(-1)
