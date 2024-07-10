# this module will be conditionally imported in patch.py for now
# in the future, we may want to move the esm features of ipyreact
# into a separate package, and then we can import it unconditionally
import logging
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Union

import ipyreact.importmap
import ipyreact.module

from solara.server import kernel_context

logger = logging.getLogger("solara.server.esm")
lock = threading.Lock()

_modules: Dict[str, Tuple[Union[str, Path], List[str]]] = {}
_modules_added_per_kernel: Dict[str, Dict[str, ipyreact.module.Module]] = defaultdict(dict)
_import_map_per_kernel: Dict[str, ipyreact.importmap.ImportMap] = {}


# in solara server, we'll monkey patch ipyreact.module with this
def define_module(name, module: Union[str, Path]):
    # collect the dependencies at this moment
    dependencies = list(_modules.keys())
    logger.info("define module %s %s (dependencies=%r)", name, module, dependencies)
    if name in _modules:
        old_module, dependencies = _modules[name]
    _modules[name] = (module, dependencies)
    if kernel_context.has_current_context():
        create_modules()
    return None


def get_module_names():
    return list(_modules.keys())


def create_modules():
    kernel_id = kernel_context.get_current_context().id
    _modules_added = _modules_added_per_kernel[kernel_id]
    logger.info("create modules %s", _modules)
    widgets = {}
    with lock:
        for name, (module, dependencies) in _modules.items():
            if name not in _modules_added:
                _modules_added[name] = create_module(name, module, dependencies=dependencies)
                logger.info("create module %s %s %s", name, module, dependencies)
            else:
                _modules_added[name].code = module if not isinstance(module, Path) else module.read_text(encoding="utf8")
                _modules_added[name].dependencies = dependencies
                logger.info("update module %s %s %s", name, module, dependencies)
            widgets[name] = _modules_added[name]
    return widgets


def create_module(name, module: Union[str, Path], dependencies: List[str]):
    return ipyreact.module.Module(code=module if not isinstance(module, Path) else module.read_text(encoding="utf8"), name=name, dependencies=dependencies)


def create_import_map():
    kernel_id = kernel_context.get_current_context().id
    with lock:
        if kernel_id not in _import_map_per_kernel:
            _import_map_per_kernel[kernel_id] = ipyreact.importmap.ImportMap(import_map=ipyreact.importmap._effective_import_map)
            logger.info("create import map %s", ipyreact.importmap._effective_import_map)
        else:
            _import_map_per_kernel[kernel_id].import_map = ipyreact.importmap._effective_import_map
            logger.info("update import map %s", ipyreact.importmap._effective_import_map)
    return
