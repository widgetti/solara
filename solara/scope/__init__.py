import re
import sys
import threading
from typing import MutableMapping

from .types import ObservableMutableMapping


def _in_solara_server():
    return "solara.server" in sys.modules


class ConnectionScope(ObservableMutableMapping):
    def __init__(self, name="connection"):
        super().__init__()
        self._global_dict = {}
        self.name = name
        self.lock = threading.Lock()

    def _get_dict(self) -> MutableMapping:
        if _in_solara_server():
            import solara.server.kernel_context

            context = solara.server.kernel_context.get_current_context()
            if self.name not in context.user_dicts:
                with self.lock:
                    if self.name not in context.user_dicts:
                        context.user_dicts[self.name] = {}
            return context.user_dicts[self.name]
        else:
            return self._global_dict


class ObservableDict(ObservableMutableMapping):
    def __init__(self):
        super().__init__()
        self._global_dict = {}

    def _get_dict(self) -> MutableMapping:
        return self._global_dict


worker = ObservableDict()
connection = ConnectionScope()


def get_kernel_id(ipython_fallback=True) -> str:
    """Returns the kernel id, a unique string for each virtual kernel.

    See [Understanding solara server](/docs/understanding/solara-server) for understanding the concept of virtual kernels
    and their lifetime.

    This unique ID can be useful to to implement storing state, scoped to a kernel. See [the scope example](/examples/general/scopes) for an example.

    If `ipython_fallback` is `True` (default), this function will also work in IPython notebooks, where it will return the IPython kernel id.

    """
    import solara.server.kernel_context

    try:
        context = solara.server.kernel_context.get_current_context()
    except RuntimeError as e:
        if not ipython_fallback:
            raise
        import IPython

        ipython = IPython.get_ipython()
        if not ipython or not hasattr(ipython, "kernel"):
            raise RuntimeError("Not in a kernel") from e
        kernel = ipython.kernel
        regex = r"[\\/]kernel-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.json$"
        connection_file = kernel.config["IPKernelApp"]["connection_file"]
        return re.compile(regex).search(connection_file).group(1)  # type: ignore
    return context.id


def get_session_id() -> str:
    """Returns the session id, which is stored using a browser cookie.

    See [Understanding solara server](/docs/understanding/solara-server#session) for more information about the Solara sessions.

    This unique ID can be useful to to implement storing state, scoped to a browser session. See [the scope example](/examples/general/scopes) for an example.
    """
    import solara.server.kernel_context

    context = solara.server.kernel_context.get_current_context()
    return context.session_id
