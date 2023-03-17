import logging
from typing import Dict, Optional, cast

from solara.lab import Reactive
from solara.server import settings

logger = logging.getLogger("solara.server.fastapi")
user = Reactive(cast(Optional[Dict], None))

app_base_url: Optional[str] = None


def get_logout_url():
    import urllib.parse

    global app_base_url
    if app_base_url is None:
        return "bla"
    return_to = urllib.parse.quote(app_base_url + "auth/logout")
    client_id = settings.oauth.client_id
    url = f"https://{settings.oauth.api_base_url}/{settings.oauth.logout_path}"
    if settings.oauth.logout_path.startswith("http"):
        url = settings.oauth.logout_path
    return f"{url}?returnTo={return_to}&redirect_uri={return_to}&post_logout_redirect_uri={return_to}&client_id={client_id}"
