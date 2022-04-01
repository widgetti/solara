import threading
import time
from typing import cast

import ipywidgets as widgets
import numpy as np
import react_ipywidgets as react
import react_ipywidgets.ipyvuetify as v
import react_ipywidgets.ipywidgets as w

from solara.components import MarkdownIt
from solara.hooks import use_thread

from .doc_use_download import DocUseDownload
from .docutils import IncludeComponent

x0 = np.linspace(0, 2, 100)


@react.component
def ButtonClick(label="Hi"):
    clicks, set_clicks = react.use_state(0)
    return w.Button(description=f"{label}: Clicked {clicks} times", on_click=lambda: set_clicks(clicks + 1))


@react.component
def Markdown(md: str):
    import markdown

    html = markdown.markdown(md)
    return w.HTML(value=html)


@react.component
def MarkdownEditor(md: str):
    md, set_md = react.use_state(md)
    with w.VBox() as main:
        w.Textarea(value=md, on_value=set_md)
        Markdown(md)
    return main


@react.component
def Doc():
    tab, set_tab = react.use_state(2, "tab")

    def set_meta():
        react.get_widget(main)._metadata = {"mount_id": "content2"}

    react.use_side_effect(set_meta)
    with v.Container() as main:
        with v.Alert(type="info", text=True, prominent=True, icon="mdi-school"):
            MarkdownIt("This documentation is live, and is running on Solara ☀️, find more on [Solara Github](https://github.com/widgetti/solara/)")
        with v.Tabs(v_model=tab, on_v_model=set_tab, vertical=True):
            for key in routes.keys():
                with v.Tab(children=[key]):
                    pass
            component = cast(react.core.Component, list(routes.values())[tab])
            with v.TabsItems(v_model=tab):
                component()
            #     pass
            # with v.Tab(children=["use_state"]):
            #     pass
            # with v.Tab(children=["use_effect"]):
            #     pass
            # with v.Tab(children=["use_memo"]):
            #     pass
            # with v.Tab(children=["use_reducer"]):
            #     pass
            # with v.Tab(children=["use_reducer"]):
            #     pass
            # with v.TabsItems(v_model=tab):
            #     if tab == 0:
            #         DocUseState()
            #     if tab == 1:
            #         DocUseEffect()
    return main


@react.component
def DocUseState(x=x0, ymax=5):
    with v.Container() as main:
        with w.VBox(layout={"padding": "20px", "max_width": "1024px"}):
            MarkdownIt(
                """
# use_state

```python
def use_state(initial: T, key: str = None) -> Tuple[T, Callable[[T], T]]:
    ...
```

use_state can be used to create a variable that is local to this component, and will be preserved during rerenders.

It returns a tuple with the current value, and a setter function that should be called to change the variable. A call to this setter
will trigger a rerender, and will cause the `use_state` function to return the new value on the next render.

## Simple examples

### Click button

Lets start with a Button, that renders how many times it is clicked.
        """
            )
            IncludeComponent(
                ButtonClick,
                """
import react_ipywidgets as react
import react_ipywidgets.ipywidgets as w

""",
                highlight=[6],
            )
            MarkdownIt(
                """
### Markdown editor
Lets continue with a more typical pattern, and create new new markdown component
        """
            )
            IncludeComponent(Markdown, md="# This is a custom\nMark-*down* **component**")

            MarkdownIt(
                """This component does not have state itself, the markdown text can only be set via its argument.
A common pattern is then to have its parent component manage the state, and pass it down:
"""
            )
            IncludeComponent(MarkdownEditor, md="# Edit me\nand the markdown component **will** *update*", highlight=[3, 5, 6])
            MarkdownIt(
                """Here we see the `MarkdownEditor` component using the `use_state` function to store the markdown text, while letting the `Textarea` component
                change its value"""
            )
    return main


@react.component
def CustomClickEvent():
    clicks, set_clicks = react.use_state(0)

    def attach_click_handler():
        def click_handler(*_ignore_args):
            set_clicks(clicks + 1)

        def cleanup():
            button_real.on_click(click_handler, remove=True)

        button_real: widgets.Button = react.get_widget(button)
        button_real.on_click(click_handler)
        return cleanup

    react.use_side_effect(attach_click_handler)
    button = w.Button(description=f"Clicked {clicks} times")
    return button


@react.component
def LongRunning():
    status, set_state = react.use_state("Doing nothing", key="status")
    progress, set_progress = react.use_state(0, key="progress")
    work_dependency, set_work_dependency = react.use_state(0, key="dependency")

    def do_work():
        cancel_event = threading.Event()

        def run():
            set_state("Running...")
            for i in range(101):
                time.sleep(0.1)
                set_progress(i)
                if cancel_event.is_set():
                    set_state("Cancelled")
                    break
            else:
                set_state("Done")

        def cleanup():
            cancel_event.set()
            try:
                worker_thread.join()
            except RuntimeError:
                pass  # fine, maybe it already stopped

        worker_thread = threading.Thread(target=run)
        worker_thread.start()
        return cleanup

    react.use_side_effect(do_work, [work_dependency])
    with w.VBox() as main:
        w.Label(value=status)
        w.FloatProgress(value=progress)
        w.Button(description="Restart", on_click=lambda: set_work_dependency(work_dependency + 1))
    return main


@react.component
def LongRunningEasier():
    status, set_state = react.use_state("Doing nothing", key="status")
    progress, set_progress = react.use_state(0, key="progress")
    work_dependency, set_work_dependency = react.use_state(0, key="dependency")

    def work(cancel_event: threading.Event):
        set_state("Running...")
        for i in range(101):
            time.sleep(0.1)
            set_progress(i)
            if cancel_event.is_set():
                set_state("Cancelled")
                break
        else:
            set_state("Done")

    result, _cancel, _done, _error = use_thread(work, [work_dependency])
    with w.VBox() as main:
        w.Label(value=status)
        w.FloatProgress(value=progress)
        w.Button(description="Restart", on_click=lambda: set_work_dependency(work_dependency + 1))
    return main


@react.component
def DocUseEffect(x=x0, ymax=5):
    with v.Container() as main:  # () as main:
        with w.VBox(layout={"padding": "20px", "max_width": "1024px"}):
            MarkdownIt(
                """
# use_side_effect

```python

# types used:
EffectCleanupCallable = Callable[[], None]
EffectCallable = Callable[[], Optional[EffectCleanupCallable]]

def use_side_effect(effect: EffectCallable, dependencies=None):
    ...
```

use_side_effect can be used to run a function after the widgets are created, to optionally perform so called 'side effects', while at the same time providing a
function that will clean up any side effect. Typical side effects include attaching event handlers, fetching data and starting threads or tasks.

Providing a cleanup function ensure our app can always dispose of resources when needed. If no dependencies are passed, the function will be executed after each
render phase. Before your effect function is called for the next time, the cleanup function will be called.


## Simple examples

###

Lets create a Button again, like we did in `use_state`, but now we manually attach the click handler.
        """
            )
            IncludeComponent(
                CustomClickEvent,
                """
import ipywidgets as widgets

""",
                highlight=[13, 15],
            )
            MarkdownIt(
                """
Note that we return a `cleanup` function, so `react-ipywidgets` knows how to remove the event handler again. Note that under water, `on_click` does exactly
this for you, but with much less code. Note that we use `get_widget` to get a reference to the real ipywidgets `Button`
(this function can only be called from within an effect function).

### Long running jobs

If we want to run a long running job, we do not want to do that in the render loop, since the render loop can be executed multiple times. Also, doing work
in the render loop will cause our app to be unresponsive.

A better way would be to include the long running task in a thread, which will be started by the side effect hook, as well as a cleanup function that will
stop the execution of the work.

        """
            )
            IncludeComponent(
                LongRunning,
                """

import threading
import time

""",
                highlight=[8, 29],
            )
            MarkdownIt(
                """
Note that we implement a restart by adding an extra dependency (`work_dependency`) which when changed, will cancel the previous work, and start the new thread.


Since this pattern is so common, this funtionality is included in a user hook, called `use_thread`, making is much easier to include such long runnings tasks
in your components.
"""
            )
            IncludeComponent(
                LongRunningEasier,
                """
from solara.hooks.hooks import use_thread

""",
                highlight=[1, 20],
            )

    return main


app = Doc()


routes = {"use_state": DocUseState, "use_effect": DocUseEffect, "use_download": DocUseDownload}
