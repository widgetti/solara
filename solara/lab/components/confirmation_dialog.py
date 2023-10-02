from typing import Callable, List, Union, overload

import reacton.ipyvuetify as v

import solara


@overload
def ConfirmationDialog(
    open: solara.Reactive[bool],
    *,
    on_close: Union[None, Callable[[], None]] = None,
    content: Union[str, solara.Element] = "",
    title: str = "Confirm action",
    ok: Union[str, solara.Element] = "OK",
    on_ok: Callable[[], None] = lambda: None,
    cancel: Union[str, solara.Element] = "Cancel",
    on_cancel: Callable[[], None] = lambda: None,
    children: List[solara.Element] = [],
    max_width: Union[int, str] = 500,
    persistent: bool = False,
):
    ...


# when open is a boolean, on_close should be given, otherwise a dialog can never be closed
# TODO: copy this pattern to many other components
@overload
def ConfirmationDialog(
    open: bool,
    *,
    on_close: Callable[[], None],
    content: Union[str, solara.Element] = "",
    title: str = "Confirm action",
    ok: Union[str, solara.Element] = "OK",
    on_ok: Callable[[], None] = lambda: None,
    cancel: Union[str, solara.Element] = "Cancel",
    on_cancel: Callable[[], None] = lambda: None,
    children: List[solara.Element] = [],
    max_width: Union[int, str] = 500,
    persistent: bool = False,
):
    ...


@solara.component
def ConfirmationDialog(
    open: Union[solara.Reactive[bool], bool],
    *,
    on_close: Union[None, Callable[[], None]] = None,
    content: Union[str, solara.Element] = "",
    title: str = "Confirm action",
    ok: Union[str, solara.Element] = "OK",
    on_ok: Callable[[], None] = lambda: None,
    cancel: Union[str, solara.Element] = "Cancel",
    on_cancel: Callable[[], None] = lambda: None,
    children: List[solara.Element] = [],
    max_width: Union[int, str] = 500,
    persistent: bool = False,
):
    """A dialog used to confirm a user action.

    (*Note: [This component is experimental and its API may change in the future](/docs/lab).*)

    By default, has a title, a text explaining the
    decision to be made, and two buttons "OK" and "Cancel".

    ## Basic examples

    ```solara
    import solara

    open_delete_confirmation = solara.reactive(False)

    def delete_user():
        # put your code to perform the action here
        print("User being deleted...")

    @solara.component
    def Page():
        solara.Button(label="Delete user", on_click=lambda: open_delete_confirmation.set(True))
        solara.lab.ConfirmationDialog(open_delete_confirmation, ok="Ok, Delete", on_ok=delete_user, content="Are you sure you want to delete this user?")
    ```

    ## Arguments

    * `open`: Indicates whether the dialog is being shown or not.
    * `on_open`: Callback to call when the dialog opens of closes.
    * `content`: Message that is displayed.
    * `title`: Title of the dialog.
    * `ok`: If a string, this text will be displayed on the confirmation button (default is "OK"). If a Button, it will be used instead of the default button.
    * `on_ok`: Callback to be called when the OK button is clicked.
    * `cancel`: If a string, this text will be displayed on the cancellation button (default is "Cancel"). If a Button, it will be used instead of the default
        button.
    * `on_cancel`: Callback to be called when the Cancel button is clicked. When persistent is False, clicking outside of the element or pressing esc key will
       also trigger cancel.
    * `children`: Additional components that will be shown under the dialog message, but before the buttons.
    * `max_width`: Maximum width of the dialog window.
    * `persistent`: When False (the default), clicking outside of the element or pressing esc key will trigger cancel.

    """

    def on_open(open_value):
        if not open_value:
            if on_close:
                on_close()

    open_reactive = solara.use_reactive(open, on_open)
    del open

    def close():
        open_reactive.set(False)

    user_on_click_ok = None
    user_on_click_cancel = None

    def perform_ok():
        if user_on_click_ok:
            user_on_click_ok()
        on_ok()
        close()

    def perform_cancel():
        if user_on_click_cancel:
            user_on_click_cancel()
        on_cancel()
        close()

    def on_v_model(value):
        if not value:
            on_cancel()
        open_reactive.set(value)

    with v.Dialog(
        v_model=open_reactive.value,
        on_v_model=on_v_model,
        persistent=persistent,
        max_width=max_width,
    ):
        with solara.v.Card():
            solara.v.CardTitle(children=[title])
            with solara.v.CardText(style_="min-height: 64px"):
                if isinstance(content, str):
                    solara.Text(content)
                else:
                    solara.display(content)
                if children:
                    solara.display(*children)
            with solara.v.CardActions(class_="justify-end"):
                if isinstance(cancel, str):
                    solara.Button(label=cancel, on_click=perform_cancel, text=True, classes=["grey--text", "text--darken-2"])
                else:
                    # the user may have passed in on_click already
                    user_on_click_cancel = cancel.kwargs.get("on_click")
                    # override or add our own on_click handler
                    cancel.kwargs = {**cancel.kwargs, "on_click": perform_cancel}
                    solara.display(cancel)

                # similar as cancel
                if isinstance(ok, str):
                    solara.Button(label=ok, on_click=perform_ok, dark=True, color="primary", elevation=0)
                else:
                    user_on_click_ok = ok.kwargs.get("on_click")
                    ok.kwargs = {**ok.kwargs, "on_click": perform_ok}
                    solara.display(ok)
