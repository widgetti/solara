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
from typing import Dict, List, Tuple, Union

import ipyvue.esm

from solara.server import kernel_context

logger = logging.getLogger("solara.server.esm_vue")
lock = threading.Lock()

_modules: Dict[str, Tuple[Union[str, Path], List[str]]] = {}
_modules_added_per_kernel: Dict[str, Dict[str, ipyvue.esm.Module]] = defaultdict(dict)


def define_module(name: str, module: Union[str, Path]):
    dependencies = list(_modules.keys())
    logger.info("define vue module %s %s (dependencies=%r)", name, module, dependencies)
    if name in _modules:
        _old_module, dependencies = _modules[name]
    _modules[name] = (module, dependencies)
    if kernel_context.has_current_context():
        create_modules()
    return None


def get_module_names() -> List[str]:
    return list(_modules.keys())


def _read(module: Union[str, Path]) -> str:
    return module.read_text(encoding="utf8") if isinstance(module, Path) else module


def create_modules():
    kernel_id = kernel_context.get_current_context().id
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
                widget = ipyvue.esm.Module(code=_read(module), name=name, dependencies=dependencies)
                _modules_added[name] = widget
                logger.info("create vue module %s", name)
            else:
                code = _read(module)
                if widget.code != code:
                    widget.code = code
                    logger.info("update vue module %s", name)
                if widget.dependencies != dependencies:
                    widget.dependencies = dependencies
            widgets[name] = widget
    return widgets


def cull_closed_kernels():
    with lock:
        for kernel_id in list(_modules_added_per_kernel):
            if kernel_id not in kernel_context.contexts:
                del _modules_added_per_kernel[kernel_id]
