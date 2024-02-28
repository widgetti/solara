from typing import Optional, Union

import reacton.ipyvuetify as v
import solara

from .. import auth, license


@solara.component
def AvatarMenu(image_url: Optional[str] = None, size: Union[int, str] = 40, color: str = "primary", children=[]):
    """Show a menu with the user's avatar and a list of items.

    By default the menu shows a logout button.

    ## Example

    ```solara
    import solara
    from solara_enterprise import auth

    @solara.component
    def Page():
        if not auth.user.value:
            solara.Info("Login to see your avatar")
            solara.Button("Login", icon_name="mdi-login", href=auth.get_login_url())
        else:
            auth.AvatarMenu()  # this shows the user's picture
            solara.Button("Logout", icon_name="mdi-logout", href=auth.get_logout_url())
    ```

    Note that a common use case is to put the avatar in the [AppBar](/api/app_bar).
    ```solara
    import solara
    from solara_enterprise import auth

    @solara.component
    def Page():
        solara.Title("Avatar in the app bar demo")
        if not auth.user.value:
            solara.Info("Login to see your avatar (see the button in the app bar)")
            with solara.AppBar():
                solara.Button(icon_name="mdi-login", href=auth.get_login_url(), icon=True)
        else:
            with solara.AppBar(): # this shows the user's picture in the app bar
                with auth.AvatarMenu():
                    solara.Button("Logout", icon_name="mdi-logout", href=auth.get_logout_url(), text=True)
                    solara.Button("Fake user settings", icon_name="mdi-account-cog", text=True)
            solara.Info("Logout via the appbar")
    ```

    ## Arguments

     * image_url: if not given, the picture from the user's profile will be used (OAuth only)
     * size: size of the avatar (in pixels)
     * color: color of the avatar (if no picture is available)
     * children: list of elements to show in the menu

    """
    license.check("auth")

    with v.Html(tag="div", v_on="x.on") as activator:
        Avatar(image_url=image_url, size=size, color=color)
        v.Icon(children=["mdi-menu-down"])

    if not children:
        children = [solara.Button("logout", icon_name="mdi-logout", href=auth.get_logout_url(), text=True)]

    with v.Menu(v_slots=[{"name": "activator", "children": activator, "variable": "x"}], offset_y=True) as menu:
        with v.List():
            for child in children:
                with v.ListItem(children=[child]):
                    pass
    return menu


@solara.component
def Avatar(image_url: Optional[str] = None, size: Union[int, str] = 40, color: str = "primary"):
    """Display an avatar with the user's picture or a default icon.

    ## Example

    ```solara
    import solara
    from solara_enterprise import auth

    @solara.component
    def Page():
        if not auth.user.value:
            solara.Info("Login to see your avatar")
            solara.Button("Login", icon_name="mdi-login", href=auth.get_login_url())
        else:
            auth.Avatar()  # this shows the user's picture
            solara.Button("Logout", icon_name="mdi-logout", href=auth.get_logout_url())
    ```

    ## Arguments

     * image_url: if not given, the picture from the user's profile will be used (OAuth only)
     * size: size of the avatar (in pixels)
     * color: color of the avatar (if no picture is available)
    """
    license.check("auth")
    user = auth.user.value
    if user:
        user_info = user.get("userinfo", {})
        src = image_url
        if src is None:
            src = user_info.get("picture")
        if src:
            with v.Avatar(size=size, class_="ma-2"):
                v.Img(src=src)
        else:
            with v.Avatar(size=size, color=color):
                v.Icon(children=["mdi-account"])
    else:
        with v.Avatar(size=size, color=color):
            with solara.Tooltip("No user"):
                v.Icon(children=["mdi-error"])
