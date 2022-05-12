"""
abstract base class for websocket with a sync interface.
Async implementation have to come up with a way how to do this sync (see e.g. the starlette implementation)
"""
import abc
import json
from typing import Union


class WebSocketDisconnect(Exception):
    pass


class WebsocketWrapper(abc.ABC):
    @abc.abstractmethod
    def send_text(self, data: str) -> None:
        pass

    @abc.abstractmethod
    def send_bytes(self, data: bytes) -> None:
        pass

    def send(self, data: Union[str, bytes]) -> None:
        if isinstance(data, str):
            self.send_text(data)
        elif isinstance(data, bytes):
            self.send_bytes(data)
        else:
            raise TypeError(f"{type(data)} not supported, only ")

    def send_json(self, data):
        self.send_text(json.dumps(data))

    @abc.abstractmethod
    def close(self) -> None:
        pass

    @abc.abstractmethod
    def receive(self) -> Union[str, bytes]:
        pass

    def receive_json(self):
        text = self.receive()
        return json.loads(text)
