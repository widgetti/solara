import contextlib
import logging
import os
from pathlib import Path
import pdb
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
    return os.path.normpath(path).startswith(os.path.normpath(parent))


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
