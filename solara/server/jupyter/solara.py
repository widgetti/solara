import json
import logging
import os
from pathlib import Path

import tornado.web
from jupyter_server.base.handlers import JupyterHandler
import solara.server.server as server

from solara.server.utils import path_is_child_of
import solara

logger = logging.getLogger("solara.server.jupyter.solara")


@solara.component
def Page():
    solara.Error("Hi, you should not see this, we only support ipypopout for now")


class SolaraHandler(JupyterHandler):
    async def get(self, path=None):
        try:
            # base url ends with /
            base_url = self.settings["base_url"]
            # root_path's do not end with /
            jupyter_root_path = ""
            if base_url and base_url.endswith("/"):
                jupyter_root_path = base_url[:-1]
            root_path = f"{jupyter_root_path}/solara"
            content = server.read_root(path="", root_path=root_path, jupyter_root_path=jupyter_root_path)
        except Exception as e:
            logger.exception(e)
            raise tornado.web.HTTPError(500)

        if content is None:
            raise tornado.web.HTTPError(404)

        self.set_header("Content-Type", "text/html")
        self.write(content)


# similar to voila
class MultiStaticFileHandler(tornado.web.StaticFileHandler):
    """A static file handler that 'merges' a list of directories

    If initialized like this::

        application = web.Application([
            (r"/content/(.*)", web.MultiStaticFileHandler, {"paths": ["/var/1", "/var/2"]}),
        ])

    A file will be looked up in /var/1 first, then in /var/2.

    """

    def initialize(self, paths, default_filename=None):  # type: ignore
        self.roots = paths
        super().initialize(path=paths[0], default_filename=default_filename)

    def get_absolute_path(self, root: str, path: str) -> str:  # type: ignore
        # find the first absolute path that exists
        self.root = self.roots[0]
        abspath = os.path.abspath(os.path.join(root, path))
        for root in self.roots[1:]:
            abspath = os.path.abspath(os.path.join(root, path))
            if os.path.exists(abspath):
                self.root = root  # make sure all the other methods in the base class know how to find the file
                break

        # tornado probably already does a version of this, to make sure it behaves as the rest of the solara
        # server, we do it again
        if not path_is_child_of(Path(abspath), Path(self.root)):
            raise PermissionError(f"Trying to read from outside of cache directory: {abspath} is not a subdir of {self.root}")

        return abspath


class Assets(MultiStaticFileHandler):
    def initialize(self):  # type: ignore
        super().initialize(server.asset_directories())
        logging.error("Using %r as assets directories", self.roots)


class ReadyZ(JupyterHandler):
    def get(self):
        json_data, status = server.readyz()
        json_response = json.dumps(json_data)
        self.set_header("Content-Type", "application/json")
        self.set_status(status)
        self.write(json_response)
