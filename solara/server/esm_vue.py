# Kernel-aware ES-module support for ipyvue, mirroring esm.py (ipyreact).
# ipyvue.define_module is monkey-patched (see patch.py) so modules are
# declared once at import time and materialized per kernel. Unlike the
# ipyreact variant, a redefinition recreates the Module widget when the
# kernel's previous widget was closed (e.g. by context.restart on hot
# reload), so in-place reloads actually reach the browser.
import logging
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import ipyvue.esm

from solara.server import kernel_context

logger = logging.getLogger("solara.server.esm_vue")
lock = threading.Lock()

_modules: Dict[str, Tuple[Union[str, Path], List[str]]] = {}
_modules_added_per_kernel: Dict[str, Dict[str, ipyvue.esm.Module]] = defaultdict(dict)


def define_module(name: str, module: Union[str, Path, None] = None, *, code: Optional[str] = None):
    if (module is None) == (code is None):
        raise TypeError("pass either module (url or Path) or code")
    source: Union[str, Path] = _CODE_PREFIX + code if code is not None else module  # type: ignore[assignment]
    with lock:
        dependencies = list(_modules.keys())
        logger.info("define vue module %s (dependencies=%r)", name, dependencies)
        if name in _modules:
            _old_module, dependencies = _modules[name]
        _modules[name] = (source, dependencies)
    if isinstance(module, Path):
        # rebuilding the bundle (e.g. vite build --watch) triggers a normal
        # solara reload, which re-reads the file in create_modules
        from solara.server import reload

        reload.reloader.watcher.add_file(str(module))
    if kernel_context.has_current_context():
        create_modules()
    return None


def get_module_names() -> List[str]:
    return list(_modules.keys())


def get_module_urls() -> List[str]:
    """Urls of url-backed modules, for modulepreload hints in the page."""
    with lock:
        urls = [module for module, _ in _modules.values() if isinstance(module, str) and _is_url(module)]
    from solara.server.server import versioned_url

    return [versioned_url(url) for url in urls]


# inline source is stored with this prefix so a plain str always means a url
_CODE_PREFIX = "\x00code:"


def _is_url(module: Union[str, Path]) -> bool:
    return isinstance(module, str) and not module.startswith(_CODE_PREFIX)


def _read(module: Union[str, Path]) -> str:
    if isinstance(module, Path):
        return module.read_text(encoding="utf8")
    return module[len(_CODE_PREFIX) :] if module.startswith(_CODE_PREFIX) else module


def _versioned(url: str) -> str:
    from solara.server.server import versioned_url

    return versioned_url(url)


def create_modules():
    context = kernel_context.get_current_context()
    kernel_id = context.id
    if kernel_id not in _modules_added_per_kernel:
        # widgets close with the kernel; drop our per-kernel bookkeeping too
        def cleanup(kernel_id=kernel_id) -> None:
            _modules_added_per_kernel.pop(kernel_id, None)

        context.on_close(cleanup)
    _modules_added = _modules_added_per_kernel[kernel_id]
    widgets = {}
    with lock:
        for name, (module, dependencies) in _modules.items():
            widget = _modules_added.get(name)
            if widget is not None and widget.comm is None:
                # closed by context.restart (hot reload) - a trait update
                # would go nowhere, recreate instead
                widget = None
            if widget is None:
                if _is_url(module):
                    assert isinstance(module, str)
                    widget = ipyvue.esm.Module(url=_versioned(module), name=name, dependencies=dependencies)
                else:
                    widget = ipyvue.esm.Module(code=_read(module), name=name, dependencies=dependencies)
                _modules_added[name] = widget
                logger.info("create vue module %s", name)
            elif _is_url(module):
                assert isinstance(module, str)
                url = _versioned(module)
                if widget.url != url:
                    widget.url = url
                    logger.info("update vue module url %s", name)
            else:
                code = _read(module)
                if widget.code != code:
                    widget.code = code
                    logger.info("update vue module %s", name)
                if widget.dependencies != dependencies:
                    widget.dependencies = dependencies
            widgets[name] = widget
    return widgets
