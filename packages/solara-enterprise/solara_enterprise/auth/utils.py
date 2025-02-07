import logging
import urllib.parse
from typing import Optional

from solara.routing import router_context
from solara.server import settings

logger = logging.getLogger("solara-enterprise.auth")


def get_logout_url(return_to_path: Optional[str] = None):
    if return_to_path is None:
        router = router_context.get()
        return_to_path = router.path
    if not return_to_path.startswith("/"):
        return_to_path = "/" + return_to_path
    assert settings.main.origin is not None
    url = settings.main.origin + settings.main.root_path
    return_to_app = urllib.parse.quote(url + return_to_path)
    return_to = urllib.parse.quote(url + f"/_solara/auth/logout?redirect_uri={return_to_app}")
    client_id = settings.oauth.client_id
    url = f"https://{settings.oauth.api_base_url}/{settings.oauth.logout_path}"
    if settings.oauth.logout_path.startswith("http"):
        url = settings.oauth.logout_path
    return f"{url}?returnTo={return_to}&redirect_uri={return_to}&post_logout_redirect_uri={return_to}&client_id={client_id}"


def get_login_url(return_to_path: Optional[str] = None):
    if return_to_path is None:
        router = router_context.get()
        return_to_path = router.path
    if not return_to_path.startswith("/"):
        return_to_path = "/" + return_to_path
    assert settings.main.origin is not None
    url = settings.main.origin + settings.main.root_path
    redirect_uri = urllib.parse.quote(url + return_to_path)
    root = settings.main.root_path
    return f"{root}/_solara/auth/login?redirect_uri={redirect_uri}"
