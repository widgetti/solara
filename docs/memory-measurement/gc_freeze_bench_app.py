"""Benchmark app for settings.main.gc_freeze: how expensive are full gc passes
when the process carries a big permanent baseline?

Module level (= startup state, frozen when gc_freeze is on):
- ~2 million small tuples (~250 MB, all gc-tracked) simulating the object count
  of heavy imports (torch, pandas, ...)
- a gc callback that records the duration of every collection, per generation

The per-click payload and use_task give each session cyclic per-kernel state, so
solara's kernel.gc_after_close backstop triggers a full collection after every
page close - exactly the pass gc.freeze() is meant to keep cheap. GCSTAT lines
go to stdout; the harness parses them from the server/docker logs.
"""

import asyncio
import gc
import time

import solara
import solara.lab

# the permanent baseline the gc would otherwise rescan on every full collection
BASELINE = [(i, i + 1, str(i)) for i in range(2_000_000)]

_gc_t0 = 0.0


def _gc_stat(phase, info):
    global _gc_t0
    if phase == "start":
        _gc_t0 = time.perf_counter()
    else:
        ms = (time.perf_counter() - _gc_t0) * 1000
        print(f"GCSTAT gen={info['generation']} ms={ms:.1f} collected={info['collected']}", flush=True)  # noqa


gc.callbacks.append(_gc_stat)

clicks = solara.reactive(0)


@solara.component
def Page():
    async def work():
        await asyncio.sleep(0.01)
        return list(range(125_000))  # ~4.5 MB per-kernel payload

    result = solara.lab.use_task(work, dependencies=[])

    solara.Button(label=f"Clicked: {clicks.value}", on_click=lambda: clicks.set(clicks.value + 1))
    if result.finished:
        assert result.value is not None
        solara.Text(f"payload: {len(result.value)}")
