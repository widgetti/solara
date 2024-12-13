from jupyter_server.utils import url_path_join

from solara.server.cdn_helper import cdn_url_path
from solara.server.jupyter.cdn_handler import CdnHandler
from .solara import SolaraHandler, Assets, ReadyZ


def _jupyter_server_extension_paths():
    return [{"module": "solara.server.jupyter.server_extension"}]


def _load_jupyter_server_extension(server_app):
    # a dummy app, so that server.read_root can be used
    import solara.server.app

    solara.server.app.apps["__default__"] = solara.server.app.AppScript("solara.server.jupyter.solara:Page")
    solara.server.app.apps["__default__"].init()

    web_app = server_app.web_app

    host_pattern = ".*$"
    base_url = url_path_join(web_app.settings["base_url"])

    web_app.add_handlers(
        host_pattern,
        [
            (url_path_join(base_url, f"/{cdn_url_path}/(.*)"), CdnHandler, {}),  # kept for backward compatibility
            (url_path_join(base_url, f"/solara/{cdn_url_path}/(.*)"), CdnHandler, {}),
            (url_path_join(base_url, "/solara/static/assets/(.*)"), Assets, {}),
            (url_path_join(base_url, "/solara/readyz"), ReadyZ, {}),
            (url_path_join(base_url, "/solara(.*)"), SolaraHandler, {}),
        ],
    )


# For backward compatibility
load_jupyter_server_extension = _load_jupyter_server_extension

# For future compatibility
_jupyter_server_extension_points = _jupyter_server_extension_paths
