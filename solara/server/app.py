import contextlib
import dataclasses
import importlib.util
import os
import threading
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import ipywidgets as widgets
from starlette.websockets import WebSocket

from . import kernel

COOKIE_KEY_CONTEXT_ID = "solara-context-id"


@contextlib.contextmanager
def cwd(path):
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


@dataclasses.dataclass
class AppContext:
    kernel: kernel.Kernel
    control_sockets: List[WebSocket]
    widgets: Dict[str, widgets.Widget]

    def display(self, *args):
        print(args)

    def __enter__(self):
        key = get_current_thread_key()
        current_context[key] = self

    def __exit__(self, *args):
        key = get_current_thread_key()
        current_context[key] = None

    def close(self):
        with self:
            widgets.Widget.close_all()
            # what if we reference eachother
            # import gc
            # gc.collect()


contexts: Dict[str, AppContext] = {}
# maps from thread key to AppContext, if AppContext is None, it exists, but is not set as current
current_context: Dict[str, Optional[AppContext]] = {}


def get_current_thread_key() -> str:
    thread = threading.currentThread()
    thread_key = repr(thread)
    return thread_key


def get_current_context() -> AppContext:
    thread_key = get_current_thread_key()
    if thread_key not in current_context:
        raise RuntimeError(f'Tried to get the current context for thread {thread_key}, but no known context found. This might be a bug in Solara.')
    context = current_context[thread_key]
    if context is None:
        raise RuntimeError(
            f'Tried to get the current context for thread {thread_key}, although the context is know, it was not set for this thread. This might be a bug in Solara.')
    return context


class AppType(str, Enum):
    SCRIPT = "script"
    NOTEBOOK = "notebook"
    MODULE = "module"


class AppScript:
    def __init__(self, name, default_app_name="app"):
        self.fullname = name
        self.app_name = default_app_name
        if ":" in self.fullname:
            self.name, self.app_name = self.fullname.split(":")
        else:
            self.name = name
        self.path: Path = Path(self.name)
        if self.name.endswith(".py"):
            self.type = AppType.SCRIPT
        elif self.name.endswith(".ipynb"):
            self.type = AppType.NOTEBOOK
        else:
            self.type = AppType.MODULE
            spec = importlib.util.find_spec(self.name)
            assert spec is not None
            assert spec.origin is not None
            self.path = Path(spec.origin)

    def run(self):
        context = get_current_context()
        # local_scope = {"display": display_solara, "__name__": "__main__", "__file__": filename, "__package__": "solara.examples"}
        local_scope = {"display": context.display, "__name__": "__main__", "__file__": self.path}
        ignore = list(local_scope)
        if self.type == AppType.SCRIPT:
            with open(self.path) as f:
                ast = compile(f.read(), self.path, "exec")
                exec(ast, local_scope)
        elif self.type == AppType.SCRIPT:
            import nbformat

            with cwd(Path(self.path).parent):
                nb: nbformat.NotebookNode = nbformat.read(self.path, 4)
                for cell_index, cell in enumerate(nb.cells):
                    cell_index += 1  # used 1 based
                    if cell.cell_type == "code":
                        source = cell.source
                        cell_path = f"{self.path} input cell {cell_index}"
                        ast = compile(source, cell_path, "exec")
                        exec(ast, local_scope)
        elif self.type == AppType.MODULE:
            mod = importlib.import_module(self.name)
            local_scope = mod.__dict__
        else:
            raise ValueError(self.type)

        app = local_scope.get(self.app_name)
        if app is None:
            import difflib

            options = [k for k in list(local_scope) if k not in ignore and not k.startswith("_")]
            matches = difflib.get_close_matches(self.app_name, options)
            msg = f"No object with name {self.app_name} found for {self.name} at {self.path}."
            if matches:
                msg += " Did you mean: " + " or ".join(map(repr, matches))
            else:
                msg += " We did find: " + " or ".join(map(repr, options))
            raise NameError(msg)
        return app

    async def watch_app(self):
        from watchgod import awatch

        reload = {
            "type": "reload",
            "reason": "app changed",
        }
        path = self.path
        if str(path).endswith("__init__.py"):
            # if a package, watch the whole directory
            path = path.parent
        print("Watch", path)
        async for changes in awatch(Path(path)):
            print("trigger reload", changes)
            context_values = contexts.values()
            contexts.clear()
            for context in context_values:
                for socket in context.control_sockets:
                    print(socket)
                    await socket.send_json(reload)
            print("send refresh!")
