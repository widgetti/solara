import logging
import mimetypes
import pathlib

import tornado.web
from jupyter_server.base.handlers import JupyterHandler

from solara.server.cdn_helper import default_cache_dir, get_data

logger = logging.getLogger("Solara.cdn")


class CdnHandler(JupyterHandler):
    def initialize(self, cache_directory=default_cache_dir):
        self.cache_directory = pathlib.Path(cache_directory)
        logging.info("Using %r as cache directory", self.cache_directory)

    async def get(self, path=None):
        try:
            content = get_data(self.cache_directory, path)
        except Exception as e:
            logger.warning(e)
            raise tornado.web.HTTPError(500)

        mime = mimetypes.guess_type(path)
        if mime[0] is not None:
            self.set_header("Content-Type", mime[0])
        self.write(content)
