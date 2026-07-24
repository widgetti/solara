"""Component churn INSIDE a live kernel: every click unmounts or remounts a
subcomponent holding a use_task and a ~4.5 MB payload.

The session-cycle protocol (open pages -> use -> close) only catches leaks
that are visible at kernel close. This app makes the harness exercise the
other axis: state that accumulates per component mount/unmount while the
kernel stays alive (the use_task leak was exactly that). Drive it with a
higher click count, e.g.:

    MEASURE_CLICKS=20 python measure.py churn_app.py

The payload-holding subcomponent is mounted on even click counts, so use an
even MEASURE_CLICKS. A leak shows up as idle-point growth proportional to
clicks x pages x cycles; healthy behavior is the same plateau as
kitchen_sink_app.py.
"""

import asyncio

import solara
import solara.lab

clicks = solara.reactive(0)


@solara.component
def TaskUser():
    async def work():
        await asyncio.sleep(0.01)
        return list(range(125_000))  # ~4.5 MB per mount

    result = solara.lab.use_task(work, dependencies=[])
    if result.finished:
        assert result.value is not None
        solara.Text(f"payload: {len(result.value)}")


@solara.component
def Page():
    solara.Button(label=f"Clicked: {clicks.value}", on_click=lambda: clicks.set(clicks.value + 1))
    if clicks.value % 2 == 0:
        TaskUser()
    else:
        solara.Text("unmounted")
