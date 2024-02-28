import json
import logging
from typing import Dict, Optional

from authlib.integrations.starlette_client import OAuth
from solara.server import settings
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    SimpleUser,
    UnauthenticatedUser,
)
from starlette.requests import HTTPConnection, Request
from starlette.responses import RedirectResponse

from .. import license

logger = logging.getLogger("solara.enterprise.auth.starlette")


oauth: Optional[OAuth] = None


def init():
    global oauth
    if settings.oauth.client_id:
        api_base_url = settings.oauth.api_base_url
        if not api_base_url.startswith("https://") and not api_base_url.startswith("http://"):
            api_base_url = f"https://{api_base_url}"
        oauth = OAuth()
        oauth.register(
            name="oauth1",
            client_id=settings.oauth.client_id,
            client_secret=settings.oauth.client_secret,
            api_base_url=api_base_url,
            server_metadata_url=f"{api_base_url}/.well-known/openid-configuration",
            client_kwargs={"scope": settings.oauth.scope},
        )


def check_oauth():
    assert oauth is not None
    assert oauth.oauth1 is not None
    if oauth.oauth1.client_id != settings.oauth.client_id:
        init()


init()


async def authorize(request: Request):
    check_oauth()
    assert oauth is not None
    assert oauth.oauth1 is not None

    org_url = request.session.pop("redirect_uri", settings.main.base_url + "/")

    token = await oauth.oauth1.authorize_access_token(request)
    # workaround: if token is set in the session in one piece, it is not saved, so we
    # split it up
    token.pop("id_token", None)
    user = token.pop("userinfo", None)
    request.session["token"] = json.dumps(token)
    request.session["user"] = json.dumps(user)

    return RedirectResponse(org_url)


async def logout(request: Request):
    redirect_uri = request.query_params.get("redirect_uri", "/")
    # ideally, we only remove these:
    request.session.pop("token", None)
    request.session.pop("user", None)
    request.session.pop("client_id", None)
    # but authlib sometimes leaves some stuff in the session on failed logins
    # so we clear it all
    request.session.clear()
    return RedirectResponse(redirect_uri)


async def login(request: Request, redirect_uri: Optional[str] = None):
    license.check("auth")
    check_oauth()
    assert oauth is not None
    assert oauth.oauth1 is not None
    if "redirect_uri" in request.query_params:
        # we arrived here via the auth.get_login_url() call, which means the
        # redirect_uri is in the query params
        request.session["redirect_uri"] = request.query_params["redirect_uri"]
    else:
        # otherwise we assume we got here via the solara.server.starlette method
        # where it detect we the OAuth.required=True setting, leading to a redirect
        request.session["redirect_uri"] = str(request.url.path)
    request.session["client_id"] = settings.oauth.client_id
    result = await oauth.oauth1.authorize_redirect(request, str(request.base_url) + "_solara/auth/authorize")
    return result


def get_user(request: HTTPConnection) -> Optional[Dict]:
    user = request.session.get("user")
    if user:
        user = json.loads(request.session["token"])
        user["userinfo"] = json.loads(request.session["user"])
        client_id = request.session.get("client_id")
        if client_id != settings.oauth.client_id:
            user = None
    return user


# only provides request.user.is_authenticated
class AuthBackend(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection):
        user = get_user(conn)
        if user is None:
            return AuthCredentials(), UnauthenticatedUser()
        else:
            username = "noname"
            return AuthCredentials(["authenticated"]), SimpleUser(username)
