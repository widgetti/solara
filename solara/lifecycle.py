import threading
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
        # idempotent: with kernel-scoped registrations (toestand Singleton/Computed)
        # both the owner's own cleanup and the kernel-close cleanup may run
        try:
            _on_kernel_start_callbacks.remove(kce)
        except ValueError:
            pass

    kce = _on_kernel_callback_entry(f, path, module, cleanup)
    _on_kernel_start_callbacks.append(kce)
    return cleanup


def kernel_closed_event() -> threading.Event:
    """Return the current kernel context's closed :class:`threading.Event` (design §5.5b).

    For user-managed threads: capture this inside the kernel context at thread-spawn time,
    then ``wait()`` on it (or poll ``is_set()`` as a loop guard) to stop cleanly when the
    kernel is closed - including a supersession/cull/server-shutdown close, not just a tab
    close. Raises :class:`RuntimeError` when called outside a kernel context.
    """
    # imported lazily: solara.server.kernel_context imports this module (avoid the cycle)
    from solara.server import kernel_context

    if not kernel_context.has_current_context():
        raise RuntimeError("solara.kernel_closed_event() must be called inside a kernel context")
    return kernel_context.get_current_context().closed_event
