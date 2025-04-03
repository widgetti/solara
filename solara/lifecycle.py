from types import FrameType, ModuleType
from typing import Callable, List, NamedTuple, Optional
from pathlib import Path
import inspect


class _on_kernel_callback_entry(NamedTuple):
    callback: Callable[[], Optional[Callable[[], None]]]
    callpoint: Optional[Path]
    module: Optional[ModuleType]
    cleanup: Callable[[], None]


class _on_app_start_callback_entry(NamedTuple):
    callback: Callable[[], Optional[Callable[[], None]]]
    callpoint: Optional[Path]
    module: Optional[ModuleType]
    cleanup: Callable[[], None]


_on_kernel_start_callbacks: List[_on_kernel_callback_entry] = []
_on_app_start_callbacks: List[_on_app_start_callback_entry] = []


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


def on_app_start(f: Callable[[], Optional[Callable[[], None]]]) -> Callable[[], None]:
    """Run a function when your solara app starts and optionally run a cleanup function when hot reloading occurs.

    `f` will be called on when you app is started using `solara run myapp.py`.
    The (optional) function returned by `f` will be called when your app gets reloaded, which
    happens [when you edit the app file and save it](/documentation/advanced/reference/reloading#reloading-of-python-files).

    Note that the cleanup functions are called in reverse order with respect to the order in which they were registered
    (e.g. the cleanup function of the last call to `on_app_start` will be called first).


    If a cleanup function is not provided, you might as well not use `on_app_start` at all, and put your code directly in the module.

    During hot reload, the callbacks that are added from scripts or modules that will be reloaded will be removed before the app is loaded
    again. This can cause the order of the callbacks to be different than at first run.

    ## Example

    ```python
    import solara
    import solara.lab


    @solara.lab.on_app_start
    def app_start():
        print("App started, initializing resources...")
        def cleanup():
            print("Cleaning up resources...")

    ...
    ```
    """

    root = _find_root_module_frame()
    path: Optional[Path] = None
    module: Optional[ModuleType] = None
    if root is not None:
        path_str = inspect.getsourcefile(root)
        module = inspect.getmodule(root)
        if path_str is not None:
            path = Path(path_str)

    def cleanup():
        return _on_app_start_callbacks.remove(ace)

    ace = _on_app_start_callback_entry(f, path, module, cleanup)
    _on_app_start_callbacks.append(ace)
    return cleanup
