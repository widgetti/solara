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
            import solara.server.app

            context = solara.server.app.get_current_context()
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
