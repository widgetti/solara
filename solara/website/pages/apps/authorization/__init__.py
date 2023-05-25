"""# Authorization

Authorization is a common requirement for web applications. This example shows how to implement a simple login form and
how to use `use_route` to implement authorization.

The `Layout` component checks if the current route requires authorization and if the user is logged in. If not, it
redirects to the login form.
"""
import dataclasses
from typing import Optional, cast

import solara
import solara.lab

github_url = solara.util.github_url(__file__)

route_order = ["/", "users", "admin"]


def check_auth(route, children):
    # This can be replaced by a custom function that checks if the user is
    # logged in and has the required permissions.

    # routes that are public or only for admin
    # the rest only requires login
    public_paths = ["/"]
    admin_paths = ["admin"]

    if route.path in public_paths:
        children_auth = children
    else:
        if user.value is None:
            children_auth = [LoginForm()]
        else:
            if route.path in admin_paths and not user.value.admin:
                children_auth = [solara.Error("You are not an admin")]
            else:
                children_auth = children
    return children_auth


@dataclasses.dataclass
class User:
    username: str
    admin: bool = False


user = solara.reactive(cast(Optional[User], None))
login_failed = solara.reactive(False)


def login(username: str, password: str):
    # this function can be replace by a custom username/password check
    if username == "test" and password == "test":
        user.value = User(username, admin=False)
        login_failed.value = False
    elif username == "admin" and password == "admin":
        user.value = User(username, admin=True)
        login_failed.value = False
    else:
        login_failed.value = True


@solara.component
def Page():
    solara.Markdown("This page is visible for everyone")

    solara.Markdown(__doc__)
    solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)


@solara.component
def LoginForm():
    username = solara.use_reactive("")
    password = solara.use_reactive("")
    with solara.Card("Login"):
        solara.Markdown(
            """
        This is an example login form.

          * use admin/admin to login as admin.
          * use test/test to login as a normal user.
        """
        )
        solara.InputText(label="Username", value=username)
        solara.InputText(label="Password", password=True, value=password)
        solara.Button(label="Login", on_click=lambda: login(username.value, password.value))
        if login_failed.value:
            solara.Error("Wrong username or password")


@solara.component
def Layout(children=[]):
    route, routes = solara.use_route(peek=True)
    if route is None:
        return solara.Error("Route not found")

    children = check_auth(route, children)

    with solara.AppLayout(children=children, navigation=True):
        with solara.AppBar():
            with solara.lab.Tabs(align="center"):
                for route in routes:
                    name = route.path if route.path != "/" else "Home"
                    is_admin = user.value and user.value.admin
                    # we could skip the admin tab if the user is not an admin
                    # if route.path == "admin" and not is_admin:
                    #     continue
                    # in this case we disable the tab
                    disabled = route.path == "admin" and not is_admin
                    solara.lab.Tab(name, path_or_route=route, disabled=disabled)
            if user.value:
                solara.Text(f"Logged in as {user.value.username} as {'admin' if user.value.admin else 'user'}")
                with solara.Tooltip("Logout"):
                    solara.Button(icon_name="mdi-logout", icon=True, on_click=lambda: user.set(None))
            else:
                with solara.AppBar():
                    solara.Text("Not logged in")
