from typing import Callable, List, Union

import reacton.ipyvuetify as v

import solara


@solara.component
def ConfirmationDialog(
    is_open: Union[solara.Reactive[bool], bool],
    on_ok: Callable[[], None],
    on_close: Callable[[], None] = lambda: None,
    content: Union[str, solara.Element] = "",
    title: str = "Confirm action",
    ok: Union[str, solara.Element] = "OK",
    cancel: Union[str, solara.Element] = "Cancel",
    children: List[solara.Element] = [],
    max_width: Union[int, str] = 500,
    persistent: bool = True,
):
    """A dialog used to confirm a user action.

    (*Note: [This component is experimental and its API may change in the future](/docs/lab).*)

    By default, has a title, a text explaining the
    decision to be made, and two buttons "OK" and "Cancel".

    ## Basic examples

    ```solara
    import solara
    from solara.lab.components.confirmation_dialog import ConfirmationDialog

    is_open = solara.reactive(False)

    def delete_user():
        print("User being deleted...")

    @solara.component
    def Page():
        solara.Button(label="Delete user", on_click=lambda: is_open.set(True))
        ConfirmationDialog(is_open, delete_user, content="Are you sure you want to delete this user?")
    ```

    ## Arguments

    * `is_open`: Indicates whether the dialog is being shown or not.
    * `on_ok`: Callback to be called when the OK button is clicked.
    * `on_close`: Optional callback to be called when dialog is closed.
    * `content`: Message that is displayed.
    * `title`: Title of the dialog.
    * `ok`: If a string, this text will be displayed on the confirmation button (default is "OK"). If a Button, it will be used instead of the default button.
    * `cancel`: If a string, this text will be displayed on the cancellation button (default is "Cancel"). If a Button, it will be used instead of the default
        button.
    * `children`: Additional components that will be shown under the dialog message, but before the buttons.
    * `max_width`: Maximum width of the dialog window.
    * `persistent`: ...

    """

    is_open_reactive = solara.use_reactive(is_open)
    del is_open

    def perform_action(callback=None):
        on_ok()
        if callback:
            callback()
        close()

    def close():
        on_close()  # possible additional actions when closing
        is_open_reactive.set(False)

    with v.Dialog(
        v_model=is_open_reactive.value,
        on_v_model=is_open_reactive.set,
        persistent=True,
        max_width=max_width,
    ):
        with solara.Card(title=title):
            if isinstance(content, str):
                solara.Markdown(content)
            else:
                solara.display(content)
            if children:
                solara.display(*children)
            with solara.CardActions():
                if isinstance(ok, str):
                    solara.Button(label=ok, on_click=perform_action)
                else:
                    solara.display(ok)
                    action = ok.kwargs.get("on_click")
                    if action:
                        # perform both on_ok and the on_click action of the custom Button
                        ok.kwargs = {**ok.kwargs, "on_click": lambda: perform_action(callback=action)}
                    else:
                        ok.kwargs = {**ok.kwargs, "on_click": perform_action}
                if isinstance(cancel, str):
                    solara.Button(label=cancel, on_click=close)
                else:
                    solara.display(cancel)
