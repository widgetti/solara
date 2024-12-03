import json
import unittest.mock
from urllib.parse import unquote

import requests

import solara.server.telemetry


def test_telemetry_basic(mocker):
    post: unittest.mock.MagicMock = mocker.spy(requests, "post")
    solara.server.telemetry.track("test_event", {"test_prop": "test_value"})
    post.assert_called_once()
    data = json.loads(unquote(post.call_args[1]["data"])[5:])[0]  # type: ignore
    assert data["event"] == "test_event"


def test_telemetry_server_start_stopc(mocker):
    post: unittest.mock.MagicMock = mocker.spy(requests, "post")
    solara.server.telemetry.server_start()
    solara.server.telemetry.server_stop()
    post.assert_called()
    data = json.loads(unquote(post.call_args[1]["data"])[5:])[0]  # type: ignore
    assert data["event"] == "Solara server stop"
    assert data["properties"]["duration_seconds"] > 0
