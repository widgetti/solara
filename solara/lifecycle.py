from types import FrameType, ModuleType
from typing import Callable, List, NamedTuple, Optional
from pathlib import Path
import inspect


class _on_kernel_callback_entry(NamedTuple):
    callback: Callable[[], Optional[Callable[[], None]]]
    callpoint: Optional[Path]
    module: Optional[ModuleType]
    cleanup: Callable[[], None]


_on_kernel_start_callbacks: List[_on_kernel_callback_entry] = []


def _find_root_module_frame() -> Optional[FrameType]:
    # basically the module where the call stack origined from
    current_frame = inspect.currentframe()
    root_module_frame = None

    while current_frame is not None:
        if current_frame.f_code.co_name == "<module>":
            root_module_frame = current_frame
            break
        current_frame = current_frame.f_back

    return root_module_frame


def on_kernel_start(f: Callable[[], Optional[Callable[[], None]]]) -> Callable[[], None]:
    root = _find_root_module_frame()
    path: Optional[Path] = None
    module: Optional[ModuleType] = None
    if root is not None:
        path_str = inspect.getsourcefile(root)
        module = inspect.getmodule(root)
        if path_str is not None:
            path = Path(path_str)

    def cleanup():
        return _on_kernel_start_callbacks.remove(kce)

    kce = _on_kernel_callback_entry(f, path, module, cleanup)
    _on_kernel_start_callbacks.append(kce)
    return cleanup
