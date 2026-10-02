# this module will be conditionally imported in patch.py for now
# in the future, we may want to move the esm features of ipyreact
# into a separate package, and then we can import it unconditionally
import logging
import warnings
import threading
import weakref
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import ipyreact.importmap
import ipyreact.module

from solara.server import kernel_context

logger = logging.getLogger("solara.server.esm")
lock = threading.Lock()

_modules: Dict[str, Tuple[Union[str, Path], List[str]]] = {}
_modules_added_per_kernel: Dict[str, Dict[str, ipyreact.module.Module]] = defaultdict(dict)
_import_map_per_kernel: Dict[str, ipyreact.importmap.ImportMap] = {}
# serializes copy-and-apply per kernel: a thread must not publish an older copy of _modules
# after another thread of the same kernel published a newer one. Weak values: a lock lives as
# long as a thread uses it, so a hot reload (context.restart) cannot swap it under that thread,
# and a closed kernel leaves nothing behind.
_lock_per_kernel: "weakref.WeakValueDictionary[str, threading.RLock]" = weakref.WeakValueDictionary()


def _kernel_lock(kernel_id: str) -> threading.RLock:
    with lock:
        kernel_lock = _lock_per_kernel.get(kernel_id)
        if kernel_lock is None:
            kernel_lock = _lock_per_kernel[kernel_id] = threading.RLock()
        return kernel_lock


# in solara server, we'll monkey patch ipyreact.module with this
def define_module(name: str, module: Union[str, Path, None] = None, *, code: Optional[str] = None, url: Optional[str] = None):
    if sum(x is not None for x in (module, code, url)) != 1:
        raise TypeError("pass exactly one of module (a Path), code or url")
    if isinstance(module, str):
        # the pre-0.6 ipyreact API: a plain str was module code
        warnings.warn(
            "passing module code as a plain str is deprecated, use code=... (or url=... for a url)",
            DeprecationWarning,
            stacklevel=2,
        )
        code = module
        module = None
    source: Union[str, Path]
    if code is not None:
        source = _CODE_PREFIX + code
    elif url is not None:
        source = url
    else:
        assert module is not None
        source = module
    with lock:
        dependencies = list(_modules.keys())
        logger.info("define module %s (dependencies=%r)", name, dependencies)
        if name in _modules:
            old_module, dependencies = _modules[name]
        _modules[name] = (source, dependencies)
    if isinstance(module, Path):
        # rebuilding the bundle (e.g. vite/esbuild --watch) triggers a normal
        # solara reload, which re-reads the file in create_modules
        from solara.server import reload

        reload.watch_file(module)
    if kernel_context.has_current_context():
        create_modules()
    return None


def get_module_names():
    return list(_modules.keys())


def create_modules():
    context = kernel_context.get_current_context()
    kernel_id = context.id
    if kernel_id not in _modules_added_per_kernel:
        # widgets close with the kernel; drop our per-kernel bookkeeping too
        def cleanup(kernel_id=kernel_id):
            _modules_added_per_kernel.pop(kernel_id, None)
            _import_map_per_kernel.pop(kernel_id, None)

        context.on_close(cleanup)
    _modules_added = _modules_added_per_kernel[kernel_id]
    logger.info("create modules %s", _modules)
    widgets = {}
    with _kernel_lock(kernel_id):
        # the global lock only guards _modules: creating a widget sends, and the event loop takes
        # this lock for every page GET (get_module_urls)
        with lock:
            modules = list(_modules.items())
        for name, (module, dependencies) in modules:
            widget = _modules_added.get(name)
            if widget is not None and widget.comm is None:
                # closed by context.restart (hot reload) - a trait update
                # would go nowhere, recreate instead
                widget = None
            if widget is None:
                _modules_added[name] = create_module(name, module, dependencies=dependencies)
                logger.info("create module %s %s %s", name, module, dependencies)
            else:
                _modules_added[name].code = _read(module) if not _is_url(module) else _modules_added[name].code
                _modules_added[name].dependencies = dependencies
                logger.info("update module %s %s %s", name, module, dependencies)
            widgets[name] = _modules_added[name]
    return widgets


# inline source is stored with this prefix so a plain str always means a url
_CODE_PREFIX = "\x00code:"


def _is_url(module: Union[str, Path]) -> bool:
    return isinstance(module, str) and not module.startswith(_CODE_PREFIX)


def _read(module: Union[str, Path]) -> str:
    if isinstance(module, Path):
        return module.read_text(encoding="utf8")
    return module[len(_CODE_PREFIX) :] if module.startswith(_CODE_PREFIX) else module


def get_module_urls() -> List[str]:
    from solara.server.server import versioned_url

    with lock:
        urls = [module for module, _ in _modules.values() if isinstance(module, str) and _is_url(module)]
    return [versioned_url(url) for url in urls]


def create_module(name, module: Union[str, Path], dependencies: List[str]):
    from solara.server.server import versioned_url

    if _is_url(module):
        assert isinstance(module, str)
        return ipyreact.module.Module(url=versioned_url(module), name=name, dependencies=dependencies)
    return ipyreact.module.Module(code=_read(module), name=name, dependencies=dependencies)


def create_import_map():
    kernel_id = kernel_context.get_current_context().id
    # not the global lock: creating a widget sends, and the event loop takes the global lock
    with _kernel_lock(kernel_id):
        widget = _import_map_per_kernel.get(kernel_id)
        if widget is not None and widget.comm is None:
            # closed by context.restart (hot reload), recreate instead
            widget = None
        if widget is None:
            _import_map_per_kernel[kernel_id] = ipyreact.importmap.ImportMap(import_map=ipyreact.importmap._effective_import_map)
            logger.info("create import map %s", ipyreact.importmap._effective_import_map)
        else:
            _import_map_per_kernel[kernel_id].import_map = ipyreact.importmap._effective_import_map
            logger.info("update import map %s", ipyreact.importmap._effective_import_map)
    return
