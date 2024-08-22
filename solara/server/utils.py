import contextlib
import logging
import os
from pathlib import Path
import pdb
import sys
import traceback

from rich import print

logger = logging.getLogger("solara.server")


def start_error(title, msg, exception: Exception = None):
    if exception:
        traceback.print_exception(None, exception, exception.__traceback__)
    print(f"[red]{title}:\n\t[blue]{msg}")  # noqa
    os._exit(-1)


def path_is_child_of(path: Path, parent: Path) -> bool:
    # We use os.path.normpath() because we do not want to follow symlinks
    # in editable installs, since some packages are symlinked
    path_string = os.path.normpath(path)
    parent_string = os.path.normpath(parent)
    if sys.platform == "win32":
        # on windows, we sometimes get different casing (only seen on CI)
        path_string = path_string.lower()
        parent_string = parent_string.lower()
    return path_string.startswith(parent_string)


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
