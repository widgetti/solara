"""Exercises the main solara state/async features in one small app, so the
memory harness stresses more code paths than the plain click app:

- a top-level ``solara.reactive`` (per-kernel copy via the context)
- ``solara.lab.computed`` derived from it (auto-subscription machinery)
- a top-level ``@solara.lab.task`` (asyncio task tied to the kernel context)
- ``solara.lab.use_task`` inside the component (per-render task lifecycle)
- ``solara.use_reactive`` (component-local reactive)
- ~4.5 MB per-kernel payload (a list built in ``use_memo``) so each kernel owns
  real data that must be freed on cull

The harness clicks the button 3 times and then waits for the ``ALL-DONE``
text, which only renders when every feature has produced its final value.
"""

import asyncio

import solara
import solara.lab

counter = solara.reactive(0)


@solara.lab.computed
def counter_squared():
    return counter.value**2


@solara.lab.task
async def background_work():
    await asyncio.sleep(0.02)
    return f"task done for {counter.value}"


@solara.component
def Page():
    local = solara.use_reactive(0)
    # ~4.5 MB of per-kernel payload (125k boxed ints + list) that must be freed on cull
    payload = solara.use_memo(lambda: list(range(125_000)), dependencies=[])

    async def compute_local():
        await asyncio.sleep(0.02)
        return local.value * 2

    result = solara.lab.use_task(compute_local, dependencies=[local.value])

    def on_click():
        counter.value += 1
        local.value += 1
        background_work()

    solara.Button(label=f"Clicked: {counter.value}", on_click=on_click)
    solara.Text(f"squared: {counter_squared.value}")
    solara.Text(f"payload: {len(payload)}")
    if result.finished:
        solara.Text(f"use_task: {result.value}")
    if background_work.finished:
        solara.Text(f"task: {background_work.value}")
    if (
        counter.value == 3
        and counter_squared.value == 9
        and local.value == 3
        and result.finished
        and result.value == 6
        and background_work.finished
        and background_work.value == "task done for 3"
    ):
        solara.Text("ALL-DONE")
