import datetime
import json
import logging
import pdb
import queue
import struct
from typing import Set

import ipykernel
import ipykernel.kernelbase
import jupyter_client.session as session
from ipykernel.comm import CommManager
from zmq.eventloop.zmqstream import ZMQStream

import solara

from . import settings, websocket

logger = logging.getLogger("solara.server.kernel")


ipykernel_version = tuple(map(int, ipykernel.__version__.split(".")))
if ipykernel_version >= (6, 18, 0):
    import comm.base_comm

    class Comm(comm.base_comm.BaseComm):
        def __init__(self, **kwargs) -> None:
            self.kernel = ipykernel.kernelbase.Kernel.instance()
            super().__init__(**kwargs)

        def publish_msg(self, msg_type, data=None, metadata=None, buffers=None, **keys):
            data = {} if data is None else data
            metadata = {} if metadata is None else metadata
            content = dict(data=data, comm_id=self.comm_id, **keys)
            self.kernel.session.send(
                self.kernel.iopub_socket,
                msg_type,
                content,
                metadata=metadata,
                parent=self.kernel.get_parent("shell"),
                ident=self.topic,
                buffers=buffers,
            )

    comm.create_comm = Comm

    def get_comm_manager():
        from .app import get_current_context

        return get_current_context().kernel.comm_manager

    comm.get_comm_manager = get_comm_manager
# from notebook.base.zmqhandlers import serialize_binary_message
# this saves us a depdendency on notebook/jupyter_server when e.g.
# running on pyodide


def _fix_msg(msg):
    # makes sure the msg can be json serializable
    # instead of using a callable like in jupyter_client (i.e. json_default)
    # we replace the keys we know are problematic
    # this allows us to use a faster json serializer in the future
    if "header" in msg and "date" in msg["header"]:
        # this is what jupyter_client.jsonutil.json_default does
        msg["header"]["date"] = msg["header"]["date"].isoformat().replace("+00:00", "Z")
    if "parent_header" in msg and "date" in msg["parent_header"]:
        # date is already a string if it's copied from the header that is not turned into a datetime
        # maybe we should do that in server.py
        date = msg["parent_header"]["date"]
        if isinstance(date, datetime.datetime):
            msg["parent_header"]["date"] = date.isoformat().replace("+00:00", "Z")


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
    bmsg = json.dumps(msg).encode("utf8")
    buffers.insert(0, bmsg)
    nbufs = len(buffers)
    offsets = [4 * (nbufs + 1)]
    for buf in buffers[:-1]:
        offsets.append(offsets[-1] + len(buf))
    offsets_buf = struct.pack("!" + "I" * (nbufs + 1), nbufs, *offsets)
    buffers.insert(0, offsets_buf)
    return b"".join(buffers)


def deserialize_binary_message(bmsg):
    """deserialize a message from a binary blog

    Header:

    4 bytes: number of msg parts (nbufs) as 32b int
    4 * nbufs bytes: offset for each buffer as integer as 32b int

    Offsets are from the start of the buffer, including the header.

    Returns
    -------
    message dictionary
    """
    nbufs = struct.unpack("!i", bmsg[:4])[0]
    offsets = list(struct.unpack("!" + "I" * nbufs, bmsg[4 : 4 * (nbufs + 1)]))
    offsets.append(None)
    bufs = []
    for start, stop in zip(offsets[:-1], offsets[1:]):
        bufs.append(bmsg[start:stop])
    msg = json.loads(bufs[0].decode("utf8"))
    msg["buffers"] = bufs[1:]
    return msg


SESSION_KEY = b"solara"


class WebsocketStream(object):
    def __init__(self, session, channel: str):
        self.session = session
        self.channel = channel


class WebsocketStreamWrapper(ZMQStream):
    def __init__(self, websocket, channel):
        self.websocket = websocket
        self.channel = channel

    def flush(self, *ignore):
        pass


def send_websockets(websockets: Set[websocket.WebsocketWrapper], binary_msg):
    for ws in list(websockets):
        try:
            ws.send(binary_msg)
        except:  # noqa
            # in case of any issue, we simply remove it from the list
            websockets.remove(ws)


class SessionWebsocket(session.Session):
    def __init__(self, *args, **kwargs):
        super(SessionWebsocket, self).__init__(*args, **kwargs)
        self.websockets: Set[websocket.WebsocketWrapper] = set()  # map from .. msg id to websocket?

    def send(self, stream, msg_or_type, content=None, parent=None, ident=None, buffers=None, track=False, header=None, metadata=None):
        try:
            msg = self.msg(msg_or_type, content=content, parent=parent, header=header, metadata=metadata)
            _fix_msg(msg)
            msg["channel"] = stream.channel
            try:
                if buffers:
                    msg["buffers"] = [memoryview(k).cast("b") for k in buffers]
                    wire_message = serialize_binary_message(msg)
                else:
                    wire_message = json.dumps(msg)
            except Exception:
                logger.exception("Could not serialize message: %r", msg)
                if settings.main.use_pdb:
                    pdb.post_mortem()
                raise
            send_websockets(self.websockets, wire_message)
        except Exception as e:
            logger.exception("Error sending message: %s", e)


class Kernel(ipykernel.kernelbase.Kernel):
    implementation = "solara"
    implementation_version = solara.__version__
    banner = "solara"

    def __init__(self):
        super(Kernel, self).__init__()
        self.session = SessionWebsocket(parent=self, key=SESSION_KEY)
        self.msg_queue = queue.Queue()  # type: ignore
        self.stream = self.iopub_socket = WebsocketStream(self.session, "iopub")
        # on github action the next line gives a mypy error:
        # solara/server/kernel.py:111: error: "SessionWebsocket" has no attribute "stream"
        # not sure why we cannot reproduce that locally
        self.session.stream = self.iopub_socket  # type: ignore
        if ipykernel_version >= (6, 18, 0):
            # from this version on, ipykernel uses the comm package https://github.com/ipython/ipykernel/pull/973
            self.comm_manager = CommManager(parent=self, kernel=self)
            import ipywidgets.widgets.widget

            if hasattr(ipywidgets.widgets.widget, "Comm"):
                ipywidgets.widgets.widget.Comm = Comm
                ipywidgets.widgets.widget.Widget.comm.klass = Comm
        else:
            self.comm_manager = CommManager(parent=self, kernel=self)
        self.shell = None
        self.log = logging.getLogger("fake")

        comm_msg_types = ["comm_open", "comm_msg", "comm_close"]
        for msg_type in comm_msg_types:
            self.shell_handlers[msg_type] = getattr(self.comm_manager, msg_type)

    async def _flush_control_queue(self):
        pass

    # these don't work from non-main thread, and we do not care about them I think
    # TODO: it seems that if post_handler_hook is not override, the flask reload tests fails
    # for unknown reason
    def pre_handler_hook(self, *args):
        pass

    def post_handler_hook(self, *args):
        pass
