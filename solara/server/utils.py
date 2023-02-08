import contextlib
import logging
import os
import pdb
import traceback
from collections import abc

from rich import print

logger = logging.getLogger("solara.server")


def start_error(title, msg, exception: Exception = None):
    if exception:
        traceback.print_exception(None, exception, exception.__traceback__)
    print(f"[red]{title}:\n\t[blue]{msg}")  # noqa
    os._exit(-1)


def nested_get(object, dotted_name: str):
    names = dotted_name.split(".")
    for name in names:
        if isinstance(object, abc.Mapping):
            object = object.get(name)
        else:
            object = getattr(object, name)
    return object


@contextlib.contextmanager
def pdb_guard():
    from . import settings

    try:
        yield
    except Exception:
        if settings.main.use_pdb:
            logger.exception("Exception, will be handled by debugger")
            pdb.post_mortem()
        else:
            raise
