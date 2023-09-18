"""
# ConfirmationDialog

"""

from typing import Union

import solara
from solara.lab.components.confirmation_dialog import ConfirmationDialog
from solara.website.utils import apidoc

users = solara.reactive("Alice Bob Cindy Dirk Eve Fred".split())
user_to_be_deleted: solara.Reactive[Union[str, None]] = solara.reactive(users.value[0])
is_open = solara.reactive(False)


def confirm_delete():
    if user_to_be_deleted.value:
        is_open.set(True)


def delete_user():
    if user_to_be_deleted.value:
        users.set([u for u in users.value if u != user_to_be_deleted.value])
    if users.value:
        user_to_be_deleted.set(users.value[0])
    else:
        user_to_be_deleted.set(None)


@solara.component
def Page():
    """Create a list of users, a dropdown to select one, and a button to delete the
    selected user. A confirmation dialog will pop up first before deletion."""
    solara.Markdown("#### Users:")
    with solara.Column():
        for user in users.value:
            bgcolor = user.lower()[0] * 3
            solara.Text(user, style=f"width: 300px; background-color: #{bgcolor}; padding: 10px;")
        if not users.value:
            solara.Text("(no users left)")
    solara.Select(label="User to be deleted:", value=user_to_be_deleted, values=users.value, style="max-width: 400px;")
    solara.Button(
        on_click=confirm_delete,
        label=(f"Delete user: {user_to_be_deleted.value}" if user_to_be_deleted.value else "Delete user"),
        style="max-width: 400px;",
        disabled=not users.value,
    )
    ConfirmationDialog(is_open, delete_user, title="Delete user", content=f"Are you sure you want to delete user **{user_to_be_deleted.value}**?")


__doc__ += apidoc(solara.lab.components.confirmation_dialog.ConfirmationDialog.f)  # type: ignore
