import pprint

import reacton.ipyvuetify as v

try:
    from solara_enterprise import auth
except ImportError:
    auth = None
import solara as sl


@sl.component
def UserCard():
    user = auth.user.value
    if user:
        user_info = user.get("userinfo")
        if user_info:
            # based on https://v2.vuetifyjs.com/en/components/cards/#props
            with v.Card(width="400px"):
                with v.ListItem(three_line=True):
                    with v.ListItemContent():
                        sl.Div("Logged in", class_="text-overline mb-4")
                        v.ListItemTitle(children=[user_info["email"]])
                        v.ListItemSubtitle(children=["You are now logged in, log out via the app bar, or the button below"])
                    with v.ListItemAvatar():
                        auth.Avatar()

                with v.CardActions():
                    sl.Button("logout", icon_name="mdi-logout", href=auth.get_logout_url(), text=True)
        else:
            sl.Error("No user info")
    else:
        sl.Error("No user")


@sl.component
def Page():
    sl.Title("Login demo using OAuth")
    with sl.AppBar():
        if auth.user.value:
            auth.AvatarMenu()
        else:
            sl.Button(icon_name="mdi-login", href=auth.get_login_url(), icon=True)

    with sl.Column():
        if auth.user.value:
            UserCard()
            with sl.Details("Raw data"):
                sl.Markdown(
                    """
                    ### Raw user data

                    *Note: do not share this data with anyone, it contains sensitive information.*

                    This is the raw user data from the auth provider.

                    We use the `picture` field to display an avatar in the [AppBar](/api/appbar).
                """
                )
                sl.Preformatted(pprint.pformat(auth.user.value))
        else:
            sl.Markdown(
                """
            ### Login demo

            This is a demo of a login system using OAuth. You can login with your google account, github account or with a username and password.
            We are using [Auth0](https://auth0.com/) as an OAuth provider.

            """
            )
            with sl.Row():
                sl.Button("login", icon_name="mdi-login", href=auth.get_login_url())


if auth is None:
    del Page
