import contextlib
import errno
import importlib
import inspect
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

import solara.server.settings as settings

NO_WATCHDOG = False
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    import watchdog.events
except ImportError:
    pass
    NO_WATCHDOG = True
logger = logging.getLogger("solara.server.reload")


class Watcher:
    def __init__(self, files, on_change: Callable[[str], None]):
        pass

    def close(self):
        pass

    def add_file(self, file):
        pass


class WatcherDummy:
    def __init__(self, files, on_change: Callable[[str], None]):
        pass

    def close(self):
        pass

    def add_file(self, file):
        pass


if NO_WATCHDOG:
    WatcherType: Type[Watcher] = WatcherDummy  # type: ignore

else:

    class WatcherWatchdog(FileSystemEventHandler):
        def __init__(self, files, on_change: Callable[[str], None]):
            self.on_change = on_change
            self.observers: List[Any] = []
            self.directories: Set[str] = set()
            self.files: List[str] = []
            self.mtimes: Dict[str, float] = dict()
            for file in files:
                self.add_file(file)

        def close(self):
            for o in self.observers:
                o.unschedule_all()
                o.stop()
            # this makes testing slow
            # for o in self.observers:
            #     o.join()

        def add_file(self, file):
            file = os.path.abspath(os.path.realpath(file))
            if file not in self.files:
                logger.debug("Watching file %s", file)
                # record the mtime (in _watch_file) *before* publishing into self.files: the
                # watchdog dispatcher thread checks `in self.files` and then reads
                # self.mtimes[path] — the old order could raise a KeyError there, which killed
                # the dispatcher thread and silently stopped hot-reload (flaked on macOS CI,
                # where FSEvents delivers events from around stream start)
                self._watch_file(file)
                self.files.append(file)

        def _watch_file(self, file):
            self.mtimes[file] = os.path.getmtime(file)
            directory = os.path.realpath(os.path.dirname(file))
            self.watch_directory(directory)

        def watch_directory(self, directory):
            if directory not in self.directories:
                logger.debug("Watching directory %s", directory)
                observer = Observer()
                observer.schedule(self, directory, recursive=False)
                try:
                    observer.start()
                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        # from rich import print()
                        from .utils import start_error

                        start_error(
                            "inotify watch limit reached", "Read https://github.com/widgetti/solara/#how-to-fix-inotify-watch-limit-reached", exception=e
                        )

                self.observers.append(observer)
                self.directories.add(directory)

        def on_moved(self, event):
            logger.debug("Moved event: %s", event)
            if isinstance(event, watchdog.events.FileMovedEvent):
                if event.dest_path in self.files:
                    self._handle_possible_change(event.dest_path)

        def on_modified(self, event):
            logger.debug("Modified event: %s", event)
            if not event.is_directory:
                if event.src_path in self.files:
                    self._handle_possible_change(event.src_path)
                else:
                    logger.debug("Ignore file modification: %s", event.src_path)

        def _handle_possible_change(self, path: str):
            # we are on the watchdog dispatcher thread: an escaping exception kills that thread
            # and hot-reload silently stops working, so never raise here
            try:
                mtime_new = os.path.getmtime(path)
            except OSError:
                logger.debug("Could not stat %s (deleted/replaced?)", path)
                return
            mtime_old = self.mtimes.get(path)
            changed = mtime_old is not None and mtime_new > mtime_old
            self.mtimes[path] = mtime_new
            if changed:
                logger.debug("File modified: %s", path)
                try:
                    self.on_change(path)
                except:  # noqa
                    # we are in the watchdog thread here, all we can do is report
                    # and continue running (otherwise reload stops working)
                    logger.exception("Error while executing on change handler")
            else:
                logger.debug("File reported modified, but mtime did not change: %s", path)

    WatcherType = WatcherWatchdog  # type: ignore


class Reloader:
    def __init__(self, on_change: Optional[Callable[[str], None]] = None) -> None:
        self.watched_modules: Set[str] = set()
        self._first = True
        self.on_change: Optional[Callable[[str], None]] = on_change
        WatcherCls = WatcherType if settings.main.mode == "development" else WatcherDummy
        self.watcher = WatcherCls([], self._on_change)
        self.requires_reload = False
        self.ignore_modules: Set[str] = set()
        self.reload_event_next = threading.Event()
        # files registered with watch_file that handle their own changes, instead of a reload
        self.file_handlers: Dict[str, Callable[[Path], None]] = {}
        # should be set at app.directory
        self.root_path: Optional[Path] = None
        # maybe we want this mode enabled in the future via configuration
        # this is useful if you have some packages installed in editable mode
        # and you want to quick reload. However this does not always work:
        #  * https://github.com/widgetti/solara/issues/177
        #  * https://github.com/widgetti/solara/issues/148
        self.aggresive_reload = False

    def start(self):
        if self._first:
            # although we try to keep track of modules loaded (which we will watch)
            # it can happen that an import is done at runtime, that we miss (could be in a thread)
            # so we always reload all modules except the ignore_modules
            self.ignore_modules = set(sys.modules)
            logger.debug("Ignoring reloading modules: %s", self.ignore_modules)
            self._first = False

    def _on_change(self, name):
        handler = self.file_handlers.get(_normalize(name))
        if handler is not None:
            handler(Path(name))
        else:
            # flag that we need to reload all modules next time
            self.requires_reload = True
            # and forward callback
            if self.on_change:
                self.on_change(name)
        # used for testing
        self.reload_event_next.set()

    def close(self):
        self.watcher.close()

    def get_reload_module_names(self):
        if self.aggresive_reload:
            # not sure why, but if we reload pandas, the integration/reload_test.py fails
            return {
                k for k in set(sys.modules) - set(self.ignore_modules) if not (k.startswith("solara.server") or k.startswith("anyio") or k.startswith("pandas"))
            }
        else:
            reload = []
            for name in sorted(sys.modules):
                mod = sys.modules[name]
                if name.startswith("solara.server"):
                    continue  # this will break everything
                if name in self.ignore_modules:
                    continue  # nothing we imported from solara itself like starlette etc
                # we only reload modules that are in the root path
                if (getattr(mod, "__file__", None) or "").startswith(str(self.root_path)):
                    reload.append(name)
            return reload

    def reload(self):
        # before we did this:
        # # don't reload modules like solara.server and react
        # # that may cause issues (like 2 Element classes existing)
        reload_modules = self.get_reload_module_names()
        # which picks up import that are done in threads etc, but it will also reload starlette, httptools etc
        # which causes issues with exceptions and isinstance checks.
        # reload_modules = self.watched_modules
        logger.info("Reloading modules... %s", reload_modules)
        # not sure if this is needed
        importlib.invalidate_caches()
        for mod_name in sorted(reload_modules):
            # don't reload modules like solara.server and react
            # that may cause issues (like 2 Element classes existing)
            logger.debug("Reloading module %s", mod_name)
            sys.modules.pop(mod_name, None)
        # if all successful...
        self.requires_reload = False

    @contextlib.contextmanager
    def watch(self):
        """Use this context manager to execute code so that we can track loaded modules and reload them when needed"""
        if self.requires_reload:
            self.reload()

        modules_before = set(sys.modules)
        try:
            yield
        finally:
            modules_after = set(sys.modules)
            # these are imported during the 'yield'
            modules_added = modules_after - modules_before
            modules_to_consider = modules_added - set(self.watched_modules)
            # TODO: libraries that solara uses need special care
            # modules_always = {k for k in sys.modules if k.startswith("reacton")}
            # modules_to_consider = modules_to_consider | modules_always
            modules_watching = set()
            if modules_to_consider:
                logger.debug("Found modules %s", modules_to_consider)
            for modname in modules_to_consider:
                module = sys.modules[modname]
                path = None
                try:
                    path = inspect.getfile(module)
                except Exception:
                    pass
                if path and Path(path).exists():
                    if not path.startswith(sys.prefix):
                        self.watcher.add_file(path)
                        self.watched_modules.add(modname)
                        modules_watching.add(modname)
            if modules_watching:
                logger.debug("Watching modules: %s for reload", modules_watching)


# there is only a reloader, and there should be only 1 app
# that connect to the on_change
reloader = Reloader()


def _normalize(path) -> str:
    return os.path.abspath(os.path.realpath(path))


def watch_file(path: Union[str, Path], on_change: Optional[Callable[[Path], None]] = None) -> None:
    """Watch a file that is not a Python module, for hot reload.

    Use this for files your code reads at import time or render time, such as templates.
    Without `on_change`, a change to the file reloads the app, like a change to a Python module.
    With `on_change`, a change calls `on_change(path)` instead, and the app is not reloaded,
    so the callback can update what is live (e.g. widgets that use the file).

    The file must exist. A file has at most one `on_change`: a later call with `on_change`
    replaces it, a call without `on_change` keeps it. It stays registered until the server stops.
    `on_change` gets the resolved path, and runs on the file watcher thread without a kernel
    context, so enter each context in `solara.server.kernel_context.contexts` to update widgets.
    An exception raised by `on_change` is logged.
    This only has effect when the Solara server runs in development mode.
    """
    key = _normalize(path)
    reloader.watcher.add_file(key)
    if on_change is not None:
        reloader.file_handlers[key] = on_change
