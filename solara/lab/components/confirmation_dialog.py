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
    """A dialog used to confirm a user action. By default, has a title, a text explaining the
    decision to be made, and two buttons "OK" and "Cancel".

    ## Basic examples

    ```solara
    import solara

    is_open = solara.reactive(False)

    def delete_user():
        ...

    solara.ConfirmationDialog(is_open, delete_user, content="Are you sure you want to delete this user?")
    ```

    ## Arguments

    ...to be added...

    """

    is_open_reactive = solara.use_reactive(is_open)
    del is_open

    def perform_action():
        on_ok()
        close()

    def close():
        on_close()  # possible additional actions when closing
        is_open_reactive.set(False)

    if is_open_reactive.value:
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
                    if isinstance(cancel, str):
                        solara.Button(label=cancel, on_click=close)
                    else:
                        solara.display(cancel)
