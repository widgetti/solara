import json
import logging
import os
import platform
import threading
import time
import uuid
from collections import defaultdict
from typing import Dict, Optional
from urllib.parse import quote

import ipyvue
import ipyvuetify
import ipywidgets
import requests

import solara
import solara.util

from . import settings

logger = logging.getLogger("solara.server.telemetry")

_auto_restart_enabled = False
_server_user_id_override = None
_server_start_time = time.time()
# Privacy note: mixpanel does not store the IP, only the region
_server_ip = None
_platform_system = platform.system()
_platform_release = platform.release()
_python_version = platform.python_version()
_connections_per_session_daily: Dict[str, int] = defaultdict(int)
_connections_per_session_cumulative: Dict[str, int] = defaultdict(int)

_seconds_per_day = 60 * 60 * 24
_report_timeout = _seconds_per_day

solara_props = {
    "solara_version": solara.__version__,
    "ipywidgets_version": ipywidgets.__version__,
    "ipyvuetify_version": ipyvuetify.__version__,
    "ipyvue_version": ipyvue.__version__,
}
_docker = False
_compute_platform = "unknown"


def is_running_on_domino():
    return "DOMINO_PROJECT_OWNER" in os.environ


def is_running_on_sagemaker_notebook():
    return "AWS_EXECUTION_ENV" in os.environ and "SageMaker" in os.environ["AWS_EXECUTION_ENV"]


def is_running_on_azure():
    return "AZURE_NOTEBOOKS_VM" in os.environ or "AZUREML_RUN_ID" in os.environ


if solara.util.is_running_in_colab():
    _compute_platform = "colab"
elif is_running_on_domino():
    _compute_platform = "domino"
elif is_running_on_sagemaker_notebook():
    _compute_platform = "sagemaker"
elif is_running_on_azure():
    _compute_platform = "azure"

_vscode = solara.util.is_running_in_vscode()

try:
    path = "/proc/self/cgroup"
    _docker = os.path.exists("/.dockerenv") or os.path.isfile(path) and any("docker" in line for line in open(path))
except:  # noqa
    logger.exception("Failed to detect docker")


def _get_ip():
    global _server_ip
    try:
        _server_ip = requests.get("https://api.ipify.org").text
    except Exception:
        _server_ip = "failed to get IP"


def override_server_user_id(server_user_id: str):
    global _server_user_id_override
    _server_user_id_override = server_user_id


def get_server_user_id():
    return _server_user_id_override or settings.telemetry.server_user_id


def track(event: str, props: Optional[Dict] = None):
    if _auto_restart_enabled:
        return
    if not settings.telemetry.mixpanel_enable:
        return
    event_item = {
        "event": event,
        "properties": {
            "token": settings.telemetry.mixpanel_token,
            "fingerprint": settings.telemetry.server_fingerprint,
            "time": int(time.time() * 1000),
            "distinct_id": get_server_user_id(),
            # can be useful to get of session duration
            "session_id": settings.telemetry.server_session_id,
            "$insert_id": str(uuid.uuid4()),  # to de-duplicate events
            # Privacy note: mixpanel does not store the IP, only the region
            "ip": _server_ip,
            "platform_system": _platform_system,
            "platform_release": _platform_release,
            "python_version": _python_version,
            "docker": _docker,
            "compute_platform": _compute_platform,
            "vscode": _vscode,
            "solara_mode": settings.main.mode,
            **(solara_props or {}),
            **(props or {}),
        },
    }
    try:
        requests.post(
            "https://api.mixpanel.com/track/",
            headers={"content-type": "application/x-www-form-urlencoded"},
            data=f"data={quote(json.dumps([event_item]))}",
            timeout=1,
        )
    except Exception:
        pass


def _usage_stats():
    unique_session_daily = len(_connections_per_session_daily)
    unique_session_cumulative = len(_connections_per_session_cumulative)
    avg_connections_daily = sum(_connections_per_session_daily.values()) / unique_session_daily if unique_session_daily else 0
    avg_connections_cumulative = sum(_connections_per_session_cumulative.values()) / unique_session_cumulative if unique_session_cumulative else 0
    uptime_days = (time.time() - _server_start_time) / (_seconds_per_day)
    return {
        "uptime_days": uptime_days,
        "unique_session_daily": unique_session_daily,
        "avg_connections_daily": avg_connections_daily,
        "unique_session_cumulative": unique_session_cumulative,
        "avg_connections_cumulative": avg_connections_cumulative,
    }


def _track():
    global _server_start_time
    _server_start_time = time.time()
    _get_ip()
    track("Solara server start")
    while True:
        try:
            time.sleep(_report_timeout)
            track("Solara report", _usage_stats())
            _connections_per_session_daily.clear()
        except Exception:
            pass


_thread = threading.Thread(target=_track, daemon=True)


def server_start():
    if _auto_restart_enabled:
        return
    if not settings.telemetry.mixpanel_enable:
        return
    try:
        _thread.start()
    except RuntimeError:
        pass


def server_stop():
    duration = time.time() - _server_start_time
    track("Solara server stop", {"duration_seconds": duration, **_usage_stats()})


_jupyter_start_event_send = False


def jupyter_start():
    # track the usage once
    global _jupyter_start_event_send
    if _jupyter_start_event_send:
        return
    _jupyter_start_event_send = True

    def jupyter_track():
        _get_ip()
        track("Solara Jupyter use")

    try:
        threading.Thread(target=jupyter_track, daemon=True).start()
    except:  # noqa
        pass


def connection_open(session_id):
    _connections_per_session_daily[session_id] += 1
    _connections_per_session_cumulative[session_id] += 1


def connection_close(session_id):
    pass


if __name__ == "__main__":
    track("Solara test event", {"where": "command line"})
