import os
import traceback
from collections import abc

from rich import print


def start_error(title, msg, exception: Exception = None):
    if exception:
        traceback.print_exception(None, exception, exception.__traceback__)
    print(f"[red]{title}:\n\t[blue]{msg}")
    os._exit(-1)


def nested_get(object, dotted_name: str):
    names = dotted_name.split(".")
    for name in names:
        if isinstance(object, abc.Mapping):
            object = object.get(name)
        else:
            object = getattr(object, name)
    return object
