from datetime import date, datetime
from unittest.mock import Mock

from solara.server.kernel import SessionWebsocket


class Dummy:
    pass


# some libraries, such as plotly may put date and datetime objects in the json content
def test_session_datetime():
    websocket = Mock()
    stream = Dummy()
    stream.channel = "iopub"  # type: ignore
    session = SessionWebsocket()
    session.websockets.add(websocket)
    session.send(stream, {"msg_type": "test", "content": {"data": "test"}, "somedate": datetime.now()})  # type: ignore
    websocket.send.assert_called_once()


def test_session_date():
    websocket = Mock()
    stream = Dummy()
    stream.channel = "iopub"  # type: ignore
    session = SessionWebsocket()
    session.websockets.add(websocket)
    session.send(stream, {"msg_type": "test", "content": {"data": "test"}, "somedate": date.today()})  # type: ignore
    websocket.send.assert_called_once()
