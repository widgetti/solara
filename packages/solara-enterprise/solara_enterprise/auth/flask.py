import json
import logging
from typing import Dict, Optional

from authlib.integrations.flask_client import OAuth
from flask import redirect, request, session
from solara.server import settings

from .. import license

logger = logging.getLogger("solara.enterprise.auth.starlette")


oauth: Optional[OAuth] = None
_app = None


def init_flask(app):
    global _app
    _app = app
    init()


def init():
    global oauth
    assert _app is not None
    _app.secret_key = settings.oauth.client_secret
    if settings.oauth.client_id:
        api_base_url = settings.oauth.api_base_url
        if not api_base_url.startswith("https://") and not api_base_url.startswith("http://"):
            api_base_url = f"https://{api_base_url}"

        oauth = OAuth(_app)
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


def authorize():
    check_oauth()
    assert oauth is not None
    assert oauth.oauth1 is not None

    org_url = session.pop("redirect_uri", settings.main.base_url + "/")

    token = oauth.oauth1.authorize_access_token()
    # workaround: if token is set in the session in one piece, it is not saved, so we
    # split it up
    token.pop("id_token", None)
    user = token.pop("userinfo", None)
    session["token"] = json.dumps(token)
    session["user"] = json.dumps(user)

    return redirect(org_url)


def logout():
    redirect_uri = request.args.get("redirect_uri", "/")
    # ideally, we only remove these:
    session.pop("token", None)
    session.pop("user", None)
    session.pop("client_id", None)
    # but authlib sometimes leaves some stuff in the session on failed logins
    # so we clear it all
    return redirect(redirect_uri)


def login(redirect_uri: Optional[str] = None):
    license.check("auth")
    check_oauth()
    assert oauth is not None
    assert oauth.oauth1 is not None
    if "redirect_uri" in request.args:
        # we arrived here via the auth.get_login_url() call, which means the
        # redirect_uri is in the query params
        session["redirect_uri"] = request.args["redirect_uri"]
    else:
        # otherwise we assume we got here via the solara.server.starlette method
        # where it detect we the OAuth.private=True setting, leading to a redirect
        session["redirect_uri"] = str(request.url)
    session["client_id"] = settings.oauth.client_id
    callback_url = str(settings.main.base_url) + "_solara/auth/authorize"
    result = oauth.oauth1.authorize_redirect(callback_url)
    return result


def allowed():
    if settings.oauth.private:
        user = session.get("user")
        if not user:
            return False
        else:
            client_id = session.get("client_id")
            if client_id != settings.oauth.client_id:
                return False
    return True


def get_user() -> Optional[Dict]:
    user = session.get("user")
    if user:
        user = json.loads(session["token"])
        user["userinfo"] = json.loads(session["user"])
        client_id = session.get("client_id")
        if client_id != settings.oauth.client_id:
            user = None
    return user
