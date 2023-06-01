import threading
from io import TextIOBase
from typing import Callable, List, Optional

import IPython


class ThreadLocal(threading.local):
    redirect: Optional[TextIOBase] = None
    hooks: Optional[List[Callable[[str], None]]] = None


class OutStream(TextIOBase):
    """A file like object that can dispatch/redirect based on a thread local state."""

    def __init__(self, default, name):
        self._default = default
        self.name = name
        self._local = ThreadLocal()

    @property
    def _redirect(self):
        return self._local.redirect

    def write(self, string: str) -> Optional[int]:
        # self._default.write("DEBUG: [" + string + "]")
        data = string
        content = {"name": self.name, "text": data}

        kernel = IPython.get_ipython().kernel
        session = kernel.session
        msg = session.msg("stream", content)  # does it matter to not have parent, parent=self.parent_header)
        for hook in self._hooks:
            msg = hook(msg)
            if msg is None:
                return None

        dispatch = self._redirect or self._default
        return dispatch.write(string)

    @property
    def _hooks(self):
        if self._local.hooks is None:
            self._local.hooks = []
        return self._local.hooks

    def register_hook(self, hook):
        self._hooks.append(hook)

    def unregister_hook(self, hook):
        self._hooks.remove(hook)
