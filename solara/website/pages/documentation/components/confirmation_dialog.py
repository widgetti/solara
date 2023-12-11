"""
# ConfirmationDialog

"""

from typing import Union

import solara
from solara.lab.components.confirmation_dialog import ConfirmationDialog
from solara.website.utils import apidoc

title = "ConfirmationDialog"
users = solara.reactive("Alice Bob Cindy Dirk Eve Fred".split())
user_to_be_deleted: solara.Reactive[Union[str, None]] = solara.reactive(None)


def ask_to_delete_user(user):
    user_to_be_deleted.value = user


def clear_user_to_be_deleted():
    user_to_be_deleted.value = None


def delete_user():
    users.set([u for u in users.value if u != user_to_be_deleted.value])
    clear_user_to_be_deleted()


@solara.component
def Page():
    """Create a list of users with a button to delete them.

    A confirmation dialog will pop up first before deletion."""
    solara.Markdown("#### Users:")
    with solara.Column(style={"max-width": "300px"}):
        for user in users.value:
            with solara.Row(style={"align-items": "center"}):
                solara.Text(user)
                solara.v.Spacer()
                solara.Button(icon_name="mdi-delete", on_click=lambda user=user: ask_to_delete_user(user), icon=True)
        if not users.value:
            solara.Text("(no users left)")

    with ConfirmationDialog(
        user_to_be_deleted.value is not None,
        on_ok=delete_user,
        on_close=clear_user_to_be_deleted,
        ok="Ok, Delete",
        title="Delete user",
    ):
        solara.Markdown(f"Are you sure you want to delete user **{user_to_be_deleted.value}**?")


__doc__ += apidoc(solara.lab.components.confirmation_dialog.ConfirmationDialog.f)  # type: ignore
