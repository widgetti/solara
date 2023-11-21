"""
abstract base class for websocket with a sync interface.
Async implementation have to come up with a way how to do this sync (see e.g. the starlette implementation)
"""
import abc
import contextlib
import json
from typing import Union


class WebSocketDisconnect(Exception):
    pass


class WebsocketWrapper(abc.ABC):
    def __init__(self):
        self._queuing_messages = False

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
    async def receive(self) -> Union[str, bytes]:
        pass

    async def receive_json(self):
        text = await self.receive()
        return json.loads(text)

    @abc.abstractmethod
    def flush(self):
        pass

    @contextlib.contextmanager
    def hold_messages(self):
        # we're assuming this only get used from a single thread (only at server.py app loop)
        self._queuing_messages = True
        try:
            yield
        finally:
            self._queuing_messages = False
            self.flush()
