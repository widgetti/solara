# this module will be conditionally imported in patch.py for now
# in the future, we may want to move the esm features of ipyreact
# into a separate package, and then we can import it unconditionally
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Union

import ipyreact.importmap
import ipyreact.module

logger = logging.getLogger("solara.server.esm")

_modules: Dict[str, Tuple[Union[str, Path], List[str]]] = {}


# in solara server, we'll monkey patch ipyreact.module with this
def define_module(name, module: Union[str, Path]):
    # collect the dependencies at this moment
    dependencies = list(_modules.keys())
    logger.info("define module %s %s (dependencies=%r)", name, module, dependencies)
    if name in _modules:
        old_module, dependencies = _modules[name]
    _modules[name] = (module, dependencies)
    return None


def get_module_names():
    return list(_modules.keys())


def create_modules():
    logger.info("define modules %s", _modules)
    widgets = {}
    for name, (module, dependencies) in _modules.items():
        widgets[name] = create_module(name, module, dependencies=dependencies)
    return widgets


def create_module(name, module: Union[str, Path], dependencies: List[str]):
    return ipyreact.module.Module(code=module if not isinstance(module, Path) else module.read_text(encoding="utf8"), name=name, dependencies=dependencies)


def create_import_map():
    logger.info("create import map %s", ipyreact.importmap._effective_import_map)
    return ipyreact.importmap.ImportMap(import_map=ipyreact.importmap._effective_import_map)
