from typing import cast, Callable, List, Union, Optional

import solara
import reacton.ipyvuetify as v


@solara.component
def ConfirmationDialog(
    is_open_rv: solara.Reactive[bool],
    action: Callable[[], None],
    content: Union[str, solara.Element] = "",
    title: str = "Confirm action",
    on_close: Callable[[], None] = lambda: None,
    ok: Union[str, solara.Element] = "OK",
    cancel: Union[str, solara.Element] = "Cancel",
    children: List[solara.Element] = [],
):
    def perform_action():
        action()
        close()

    def close():
        on_close()  # possible additional actions when closing
        is_open_rv.set(False)

    if is_open_rv.value:
        with v.Dialog(
            #children=children,
            v_model=is_open_rv.value,
            on_v_model=is_open_rv.set,
            permanent=True,
            max_width=500,
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
