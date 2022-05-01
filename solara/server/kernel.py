import json
import logging
import struct
from typing import Any, Set

import ipykernel.kernelbase
import jupyter_client.session as session
from ipykernel.comm import CommManager
from jupyter_client.jsonutil import json_default
from jupyter_client.session import json_packer
from zmq.eventloop.zmqstream import ZMQStream

WebSocket = Any

# from notebook.base.zmqhandlers import serialize_binary_message
# this saves us a depdendency on notebook/jupyter_server when e.g.
# running on pyodide


def serialize_binary_message(msg):
    """serialize a message as a binary blob

    Header:

    4 bytes: number of msg parts (nbufs) as 32b int
    4 * nbufs bytes: offset for each buffer as integer as 32b int

    Offsets are from the start of the buffer, including the header.

    Returns
    -------

    The message serialized to bytes.

    """
    # don't modify msg or buffer list in-place
    msg = msg.copy()
    buffers = list(msg.pop("buffers"))
    bmsg = json.dumps(msg, default=json_default).encode("utf8")
    buffers.insert(0, bmsg)
    nbufs = len(buffers)
    offsets = [4 * (nbufs + 1)]
    for buf in buffers[:-1]:
        offsets.append(offsets[-1] + len(buf))
    offsets_buf = struct.pack("!" + "I" * (nbufs + 1), nbufs, *offsets)
    buffers.insert(0, offsets_buf)
    return b"".join(buffers)


SESSION_KEY = b"solara"


class WebsocketStream(object):
    def __init__(self, session, channel: str):
        self.session = session
        self.channel = channel


class BytesWrap(object):
    def __init__(self, bytes):
        self.bytes = bytes


class WebsocketStreamWrapper(ZMQStream):
    def __init__(self, websocket, channel):
        self.websocket = websocket
        self.channel = channel

    def flush(self, *ignore):
        pass


def send_websockets(websockets, binary_msg):
    # for pyiodide/flask we can do sth like this
    # for ws in list(self.websockets):
    #     ws.send(binary_msg)
    for ws in websockets:

        async def sendit(binary_msg, ws=ws):
            try:
                await ws.send_bytes(binary_msg)
            except Exception:
                if ws in websockets:
                    websockets.remove(ws)

        try:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                had_loop = True
            except RuntimeError:
                had_loop = False
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if loop is None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if not had_loop:
                asyncio.run(sendit(binary_msg))
            else:
                try:
                    asyncio.create_task(sendit(binary_msg))
                except RuntimeError:
                    asyncio.run(sendit(binary_msg))
        except:  # noqa: E722
            logging.exception("sending websocket")


class SessionWebsocket(session.Session):
    def __init__(self, *args, **kwargs):
        super(SessionWebsocket, self).__init__(*args, **kwargs)
        self.websockets: Set[WebSocket] = set()  # map from .. msg id to websocket?

    def send(self, stream, msg_or_type, content=None, parent=None, ident=None, buffers=None, track=False, header=None, metadata=None):
        try:
            msg = self.msg(msg_or_type, content=content, parent=parent, header=header, metadata=metadata)
            msg["channel"] = stream.channel
            if buffers:
                msg["buffers"] = [memoryview(k).cast("b") for k in buffers]
                binary_msg = serialize_binary_message(msg)
            else:
                binary_msg = json_packer(msg).decode("utf8")
            # if not self.websockets:
            #     print("unknown", msg)
            # else:
            #     print(self.websockets)
            # print(msg, self.websockets)
            send_websockets(self.websockets, binary_msg)
        except Exception as e:
            print(e)


class Kernel(ipykernel.kernelbase.Kernel):
    implementation = "ipython"
    implementation_version = "0.1"
    banner = "banner"

    def __init__(self):
        super(Kernel, self).__init__()
        self.session = SessionWebsocket(parent=self, key=SESSION_KEY)

        self.stream = self.iopub_socket = WebsocketStream(self.session, "iopub")
        self.session.stream = self.iopub_socket
        self.comm_manager = CommManager(parent=self, kernel=self)
        self.shell = None
        self.log = logging.getLogger("fake")

        comm_msg_types = ["comm_open", "comm_msg", "comm_close"]
        for msg_type in comm_msg_types:
            self.shell_handlers[msg_type] = getattr(self.comm_manager, msg_type)

    async def _flush_control_queue(self):
        pass
