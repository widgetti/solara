# Memory Measurement Handbook

A handoff document for measuring memory use of a long-running Python server
(any project — the worked examples are Solara apps). It tells you **how to
measure**, **which numbers to trust on which platform**, **what healthy looks
like**, and **how to decide "leak or not"**. It is written to be executable by
an LLM agent or a human without extra context.

Every claim marked **Measured**/**Verified** was confirmed by experiment
(July 2026, macOS/arm64 + docker Linux, Python 3.11, solara 1.59.0). The
reference harness lives in [memory-measurement/](memory-measurement/) and
`check_assumptions.py` there re-verifies the micro-claims.

Companion: [memory-leak-detection.md](memory-leak-detection.md) — object-level
leak hunting (weakrefs, objgraph, retention chains). This document tells you
*whether and where* memory grows; that one tells you *why an object is still
alive* once you know something leaks.

## TL;DR protocol (start here)

1. Run the server under a **cycle workload**: open N realistic sessions, use
   them, close them, wait until the app confirms cleanup, let it settle,
   measure. Repeat ≥ 10 cycles. (Reference implementation: `measure.py` /
   `measure_docker.py`.)
2. Measure **from outside the process**, using the right metric:
   - Linux: `anon` from cgroup `memory.stat` (best) or `psutil` RSS/USS
   - macOS: `vmmap -summary <pid>` "Physical footprint" — **never RSS**
3. Plot the idle-point number per cycle and read the shape:
   - **Decaying increments → plateau**: healthy. That is allocator retention.
   - **Constant increment per cycle**: leak. The increment is your leak rate.
4. Per-session cost = (loaded − idle) / N, after at least one warmup cycle.
5. Verify cleanup independently of memory: an app-level counter endpoint
   (Solara: `/resourcez`) must return to baseline every cycle. "Memory not
   freed" is often just "cleanup didn't run".
6. **Also churn WITHIN a session**: repeatedly create and destroy the app's
   sub-resources while the session stays open (mount/unmount components,
   open/close panels — `churn_app.py`). The session cycle only catches leaks
   visible at session close; per-mount accumulation inside a live session is
   invisible to it (that blind spot hid a real `use_task` leak, see the case
   study below).

## Why the OS number does not tell the full story

There are three layers of memory management stacked on top of each other.
Memory freed at one layer is often *not* returned to the layer below:

```
Python objects        (gc, refcounting)
      ↓ freed objects go back to...
pymalloc arenas       (CPython's small-object allocator, obmalloc)
      ↓ empty arenas go back to...
libc malloc / mmap    (glibc holds freed memory in arenas too)
      ↓ trimmed pages go back to...
OS                    (this is what RSS measures)
```

Consequences:

- **pymalloc only returns an arena to the OS when it is completely empty.**
  One surviving small object (a few hundred bytes) can pin an entire arena
  (1 MiB on Python 3.10+, 256 KiB before). **Measured** (macOS, Python 3.11):
  allocating 4 million small tuples grows RSS by ~548 MB; freeing *all* of
  them returns almost everything (+36 MB left); but freeing 99.9% and keeping
  every 1000th tuple returns *nothing* (+582 MB still resident).
  Fragmentation, not volume, is what pins memory.
- **glibc malloc keeps freed memory too** (per-thread arenas, trim
  thresholds). Threads make this worse: `MALLOC_ARENA_MAX=2` is a common
  mitigation on thread-heavy Linux servers.
- **RSS counts shared pages** (loaded `.so` files, forked copy-on-write
  pages). For per-process cost, USS (unique set size) is more honest.

**The one rule this implies:** never judge a single absolute number. A
high-but-stable value after load is allocator retention; a value that keeps
*growing* under a repeated identical workload is a leak. Measure the trend
over cycles.

## Which metric to trust, per platform

Ranked by trustworthiness. All of this is **measured**, see the worked
example below.

1. **Linux cgroup `anon`** (`grep '^anon ' /sys/fs/cgroup/memory.stat`) —
   anonymous (heap) pages, no page-cache pollution, no compressor games. The
   production metric. Trap: `memory.current` includes page cache — measured
   405 MB `current` when `anon` was 109 MB (the difference was pip's page
   cache). Never size pods on `memory.current` without checking `memory.stat`.
   `memory.peak` is the high-water mark you size pods with (same caveat).
2. **macOS physical footprint** (`vmmap -summary <pid> | grep "Physical
   footprint"`) — what Activity Monitor shows; includes compressed pages.
   Stable and load-correlated. Fine for local development.
3. **Process RSS via psutil** — fine on Linux; on macOS **do not use for
   trends**: the memory compressor takes idle dirty pages out of RSS, so it
   *drops* while the app is idle and bounces unpredictably. Measured on a
   solara server: RSS swung 70–142 MB across identical load cycles; per-user
   deltas computed from it were pure noise (−5 to +5 MB for the same
   workload).

More macOS traps (measured):

- `psutil.Process().memory_full_info()` (USS) raises `AccessDenied` unless
  root. USS is effectively a Linux metric.
- `resource.getrusage(...).ru_maxrss` (peak, useful in tests) is **bytes** on
  macOS but **kilobytes** on Linux.

```python
import psutil
p = psutil.Process()
p.memory_info().rss          # OK on Linux; macOS: trends unreliable
p.memory_full_info().uss     # Linux only in practice
```

```bash
vmmap -summary <pid> | grep "Physical footprint"
# Physical footprint:         119.3M
# Physical footprint (peak):  145.6M
```

## The cycle protocol, in detail

The transferable core. Adapt the constants, keep the structure:

1. **Start the server** as a subprocess (measure from outside — in-process
   measurement changes what you measure). Set cleanup timeouts low so the
   test does not wait hours (Solara: `SOLARA_KERNEL_CULL_TIMEOUT=0.5s`).
2. **Warm up**: one full session open/use/close, wait for cleanup. The first
   session pays one-time import and cache costs; never include it in
   per-session math.
3. **Per cycle** (≥ 10 cycles):
   a. record idle memory,
   b. open N real sessions (real browser pages, not bare HTTP — a session
      must exercise the websocket/kernel/render path), N ≥ 10 so per-session
      cost dominates noise,
   c. *use* each session (click, wait for the rendered result — otherwise you
      measure connection setup, not the app), and if the app has async work,
      wait for a completion marker,
   d. record loaded memory,
   e. close all sessions,
   f. **wait for the app to confirm cleanup** (poll the counter endpoint
      until sessions == 0) — never use a fixed sleep,
   g. settle ~2 s, record idle memory again.
4. **Read the results**:
   - per-session cost = (loaded − idle-before) / N,
   - idle-point series over cycles → plateau (healthy) or line (leak),
   - counters (sessions/threads/websockets) must return to baseline every
     cycle — if they don't, fix that first; the memory question is moot.

**The second axis: churn within a session.** The cycle above varies the
number of *sessions*; every leak it can catch is one that survives session
close. State that accumulates per *component* (or per sub-resource) while
the session stays open is invisible to it — closing the session frees the
accumulation before the measurement can see it, and a handful of
interactions per session is lost in the noise. So also run the protocol
with a workload that repeatedly creates and destroys sub-resources inside
each session (`churn_app.py`: every click mounts or unmounts a
`use_task` + 4.5 MB payload subcomponent; drive it with
`MEASURE_CLICKS=10` or more). Same read-out: idle-point plateau vs line.
The object-level twin is a weakref test: mount/unmount N times in one live
kernel and assert at most the mounted instance's payload stays alive
(`tests/unit/task_test.py::test_use_task_unmounted_instance_is_collected`).

Reference implementation in [memory-measurement/](memory-measurement/):

- `click_app.py` — minimal one-button app (framework floor)
- `kitchen_sink_app.py` — exercises reactive/computed/task/use_task/
  use_reactive plus ~4.5 MB per-session payload; renders `ALL-DONE` when
  every feature finished (the harness waits for it)
- `churn_app.py` — within-session churn: each click mounts/unmounts a
  subcomponent holding a `use_task` + ~4.5 MB payload
- `measure.py [app.py] [marker]` — host run (psutil + vmmap), prints per-cycle
  table, writes `report-<app>.json`; `MEASURE_CLICKS`/`MEASURE_PORT` override
  the defaults
- `measure_docker.py [app.py] [marker]` — same protocol against a 512 MB
  `python:3.11-slim` container, reading cgroup v2 numbers (the browser stays
  on the host so the cgroup contains only the server)
- `check_assumptions.py` — re-verifies the measured micro-claims in this doc

## Ground truth: run under a hard memory limit

When the question is operational — "how many users fit in a 512 MB pod?" —
let the kernel be the judge. A cgroup limit counts *real* pages, including
allocator retention and native buffers, exactly like production:

```bash
# Disable swap headroom (--memory-swap == --memory) so the container OOMs
# instead of silently thrashing.
docker run --rm -it --memory 512m --memory-swap 512m \
    -p 8765:8765 -v $PWD:/app -w /app python:3.11-slim \
    sh -c "pip install solara && solara run app.py --host 0.0.0.0"

docker stats                        # live per-container usage
# inside the container (cgroup v2):
cat /sys/fs/cgroup/memory.current   # in use now (incl. page cache!)
cat /sys/fs/cgroup/memory.peak      # high-water mark
grep '^anon ' /sys/fs/cgroup/memory.stat   # the honest heap number
```

- On macOS, docker runs a Linux VM, so this also gives you production glibc
  behavior — more representative than profiling the Mac host.
- `resource.setrlimit(RLIMIT_AS)` / `ulimit -v` is a docker-free variant on
  Linux, but it limits *virtual* address space and trips over harmless big
  `mmap` reservations; not enforced on macOS. Prefer the cgroup.

## Tool layers for diagnosis

Once the protocol says "memory grows", use these to find where.

### Python-level: tracemalloc, gc, _debugmallocstats

```python
import tracemalloc
tracemalloc.start(10)                      # keep 10 stack frames per allocation
snap1 = tracemalloc.take_snapshot()
# ... one or more workload cycles ...
snap2 = tracemalloc.take_snapshot()
for stat in snap2.compare_to(snap1, "lineno")[:15]:
    print(stat)
```

Enable without code changes: `PYTHONTRACEMALLOC=10 solara run app.py`.

Coverage — **measured**: a 50 MB numpy array *is* visible to tracemalloc
(modern numpy registers its buffers), but 50 MB of raw `malloc` via ctypes
shows up as 0 bytes. C extensions that allocate outside the Python allocator
(zmq buffers, arrow pools, GUI toolkits) are invisible — that's memray's job.

```python
import sys, gc
from collections import Counter

sys.getallocatedblocks()   # live allocations Python knows about
sys._debugmallocstats()    # pymalloc arena/pool stats: how full are the arenas?
# writes to C-level stderr: contextlib.redirect_stderr CANNOT capture it,
# redirect fd 2 instead (python app.py 2>stats.txt)

Counter(type(o).__name__ for o in gc.get_objects()).most_common(20)
```

`_debugmallocstats` answers "Python does its own memory management — what is
it holding?": many arenas at low utilization = fragmentation; the space will
be reused before the OS is asked for more.

### Whole-process: memray

[memray](https://bloomberg.github.io/memray/) (Linux + macOS) intercepts the
allocator functions themselves (`malloc`, `free`, `mmap`, plus Python
allocator hooks), so it sees native C-extension memory too. Know your mode:

- **Default:** pymalloc stays on — small Python objects appear as big arena
  `mmap`s attributed to whatever triggered arena creation. Good for native
  memory, misleading for fine-grained Python attribution.
- **`--trace-python-allocators`:** records individual Python allocations.
  Slower, bigger files, per-object attribution.
- **`PYTHONMALLOC=malloc` + `memray flamegraph --leaks`:** for leak analysis
  disable pymalloc so every Python object is a real `malloc`; otherwise block
  reuse makes freed memory look leaked and vice versa.
- **`--native`:** adds C/C++ frames — finds *which extension* owns the memory.

```bash
memray run -o out.bin -m solara run app.py --production
# exercise, Ctrl-C, then:
memray flamegraph out.bin           # who holds memory at the peak
memray flamegraph --leaks out.bin   # what was never freed (PYTHONMALLOC=malloc!)
memray stats out.bin
memray run --live -m solara run app.py    # live TUI
memray attach <pid>                       # running process (needs lldb/gdb)
```

**Verified** on a real solara server: `memray run -m solara run app.py` works
as-is; its reported peak (118.4 MB) matched the vmmap physical footprint of an
unprofiled server (~119 MB) within 1 MB; the flamegraph attributed ~37 MB
(~30% of peak) to module imports at startup. Verified in a synthetic test:
a never-freed ctypes `malloc` and kept-alive Python objects both appear in
`--leaks` output under the correct function names. Traps: `memray tree` opens
an interactive TUI (use `flamegraph`/`stats`/`summary` in scripts); the
temporal view is `memray flamegraph --temporal`.

What memray does *not* answer: **why** an object is still alive. For
retention chains use `objgraph` per
[memory-leak-detection.md](memory-leak-detection.md).

## What to expect: measured baselines (Solara, calibration numbers)

Protocol: 10 pages/cycle × 10 cycles = 100 kernel lifecycles per run, 3 clicks
per page, `solara run --production`, real Chromium sessions.

### Minimal click app (framework floor)

| Metric | Value |
|--------|-------|
| Startup heap (Linux cgroup `anon`) | ~96 MB |
| Steady-state plateau | ~109 MB |
| macOS physical footprint idle / startup-peak | ~119–125 MB / 146 MB |
| Per-kernel, first cycle (cold pools) | ~0.6 MB |
| Per-kernel, steady state | ~0.02–0.1 MB (reuses warm pools) |
| Threads | stable ~19–23 over 100 kernels |
| Module imports share of baseline | ~37 MB (memray) |

### Kitchen-sink app (reactive + computed + task + use_task + use_reactive + ~4.5 MB payload/kernel)

`kitchen_sink_app.py` exercises the async/state machinery and gives every
kernel a ~4.5 MB payload. Same protocol, and a very different — and
instructive — result:

| Metric | Value |
|--------|-------|
| Per-kernel, first cycle | ~4.5–5 MB (the payload, as expected) |
| Idle heap over cycles (Linux `anon`) | **sawtooth**: 100 → 213 → drop to 181 → 221 → drop to 209 MB |
| macOS physical footprint | same sawtooth: 174 → 231 → drop to 175 → ~195 MB |
| `/resourcez` after every cycle | kernels 0, websockets closed == attempts, threads bounded (~28 active after 1540 created) |
| Weakref leak test, naive harness | **flaky**: leaked in 4/7 runs |
| Weakref leak test, log-records cleared | 8/8 pass in ~3.5 s → **no production leak** |

**Interpretation (this is the case study to learn from):**

1. The sawtooth (rise, periodic sharp drop) means the memory *is* reclaimable
   but only when a generation-2 GC runs: the closed kernels became **cyclic
   garbage**, not leaked objects. Solara deliberately avoids `gc.collect()` on
   kernel close (latency), so big per-kernel payloads wait for the collector's
   own schedule. A plain "it keeps growing" reading over too few cycles would
   have called this a leak; the drops disprove that. When in doubt, run more
   cycles or force `gc.collect()` inside the server and see if the level
   resets.
2. Root cause of the cycles: a task-cancel race. Re-clicking / disconnecting
   cancels a running `@solara.lab.task`; the task thread schedules
   `future.set_exception(CancelledError)` onto the kernel loop, the future is
   sometimes already done, and the resulting `InvalidStateError` is logged by
   asyncio **with the exception traceback attached**. Exception tracebacks are
   reference bombs: the `CancelledError.__traceback__` held 5 coroutine frames
   whose locals referenced the whole `VirtualKernelContext` (and its 4.5 MB
   payload). Those exception→frames→context chains sit in reference cycles
   (partly on the closed kernel event loop's pending-callback list) until
   gen-2 GC.
3. **In tests this becomes a hard, flaky leak**: pytest's `LogCaptureHandler`
   retains every `LogRecord`, including the traceback, so whether the weakref
   test failed depended on whether the race fired (it did in roughly half the
   runs). The fix in the leak test (`tests/integration/kitchen_sink_leak_test.py`)
   is to clear captured log records *continuously* in the GC loop — records
   can be emitted seconds later while task threads wind down (a one-time clear
   still failed; continuous clearing passed 8/8 in ~3.5 s). Any leak-test
   harness that captures logs needs this, or it will report phantom leaks.
4. Bounded, expected retention that is *not* a leak: task threads hold frames
   (and thus the context) for a few seconds after close; log records hold
   tracebacks until dropped. Distinguish "held for seconds" from "held
   forever" by letting the GC loop run tens of seconds before concluding.

Practical consequences: apps that trigger task cancellations (fast re-clicks,
disconnects mid-task) will idle at a higher, spikier memory level than
plateau apps — size capacity on the sawtooth peaks, not the plateau. And any
`Exception` object stored in a long-lived structure should be stripped
(`exc.__traceback__ = None`) or it pins every frame it passed through.

### The follow-up: hunting and breaking the cycles at the source

The sawtooth was fixed by making closed kernel contexts collectable by plain
refcounting. The hunting technique is general and worth stealing:

1. **Disable gc and watch a weakref.** `gc.disable()` stops *automatic*
   collection but leaves refcounting intact (and explicit `gc.collect()` still
   works). Run one session, close it, wait a few seconds, and check a weakref
   to the session object. If it resolves, whatever holds it is a reference
   cycle (or a genuine external root) you can now inspect *intact* — forced
   collection would have destroyed the evidence.
2. **Walk `gc.get_referrers()` upward, printing edges** as
   `OwnerType.attribute` (find a dict's owner by checking which object has it
   as `__dict__`). Two traps: your analyzer's own result lists show up as
   referrers (track and filter their `id()`s), and your own stack frames do
   too (filter by `f_code.co_name`).
3. **Break the edge in the close/cleanup path**, rerun, repeat until the
   weakref dies by refcount alone.

What this found in solara (all fixed by breaking the edge in the close path):

- `context._last_kernel_cull_task` → cancelled asyncio task →
  `CancelledError.__traceback__` → `kernel_cull` frame → closure cell `self`
  → context. Fix: drop the task/future references in `close()` right after
  cancelling them. This one affected *every* app, even the minimal one.
- `TaskAsyncio.current_task` → finished/cancelled asyncio task → its
  contextvars copy and exception traceback → kernel context. Fix: a
  `context.on_close` callback clears the task bookkeeping
  (`_drop_call_state`).
- `context.app_object` kept referencing the closed render context. Fix:
  `close()` drops it after closing.

What it found one layer down (fixed in reacton,
[widgetti/reacton#52](https://github.com/widgetti/reacton/pull/52)): the hook
state tree stores `use_state` setter closures
(`reacton.core._RenderContext.make_setter.<locals>.set_`) whose cells point
back at the render context, and the setters are also captured by
solara/ipywidgets callback closures. So the render tree — which owns
`use_memo` payloads — stayed one big cycle even after `rc.close()`.

The fix is instructive because the obvious approach is **wrong**: capturing
the render context weakly in those closures was tried in 2023 and reverted
(reacton `cf61378`) — a setter can legitimately be the *only* reference
keeping its component context alive (held by another component's callback
after an unmount), and with weak captures, gc timing decides whether that
setter still works. Instead, the closures keep their strong references and
`rc.close()` now empties every component context (elements, children, hook
state, effects — snapshotted before `_remove_element` detaches them, and
*replacing* the containers rather than clearing them, since `state_get()`
hands out the live state dicts). Whoever still holds a setter or handler
after close keeps only a small hollow context alive, and `set_` /
`force_update` are no-ops once the context is closing.

And one non-solara ghost to know about: **playwright's sync API captures
`inspect.stack()`** (`__pw_stack__`) on every `goto`/`click`/`wait_for`, so in
a playwright-driven test the test function's own frame (and every local in
it) is retained by playwright, not by your server. A gc-disabled leak check
cannot pass under playwright for this reason — do refcount-hygiene checks
with the diagnostic above, and keep CI leak tests on the forced-gc pattern.

The backstop: `settings.kernel.gc_after_close` (default on, only for kernels
that actually rendered an app) schedules one deferred, coalesced
`gc.collect()` on a background thread ~1 s after a kernel closes. With the
reacton fix it is genuinely just insurance for reference cycles in *user*
code — and for running against a reacton release that predates the fix,
where disabling it brings the sawtooth back (measured: Linux `anon`
100→221 MB with drops).

**Measured on the merged fixes** (kitchen-sink app, 10 pages × 10 cycles):

| Configuration | Idle level | Peak |
|---|---|---|
| Before the fixes | sawtooth, gen-2 gc lag | 231 MB (macOS footprint) |
| solara + reacton fixes, backstop on | plateau ~168 MB | 180 MB |
| solara + reacton fixes, **gc disabled** | plateau ~168 MB | 178 MB |
| Linux cgroup `anon`, backstop on | plateau ~162 MB | ~162 MB |

Memory returns after every close cycle in all fixed configurations — pure
refcounting does the work; the gc-disabled and default runs are essentially
identical.

Two traps from implementing the backstop: a thread started while a context
closes must not inherit that context (solara patches `Thread` to propagate
contexts, and a context whose `kernel` is already `None` hung
`Thread.start()` forever), and a gc storm from many short-lived contexts
pauses all threads — the unit test suite closes one context per test, and
the GIL pauses broke timing-sensitive tests on loaded CI runners (hence the
rendered-an-app gate).

### Case study 2: the use_task leak the protocol missed

After all of the above was measured, verified, and released, a user found a
leak in `use_task` — a lesson in methodology, because every measurement and
test above was green while it existed.

**Why it was invisible**: every workload cycled *sessions* — mount, use
briefly, close, assert everything freed. `use_task` leaked **per component
mount**: each mount created a `Task` inside a `Singleton`, whose constructor
registered a reset callback in the process-global `on_kernel_start` list and
discarded the returned unregister-cleanup. Fine for module-level `@task`
(one instance per process, the module pins it anyway); for `use_task` every
mount permanently pinned a task instance plus its `._last_value` result. A
session that mounts/unmounts such components grows without bound — but close
the session and everything except the global registrations is freed, so
close-path tests pass, and three clicks per session is invisible in the
per-session noise. The kitchen-sink app never unmounted anything.

**The fix** (`use_task` cleanup on unmount, solara #1180) had its own
instructive race: clearing the kernel-store entries at unmount was not
enough, because a worker thread *just finishing* re-created the entry via
its result write. The cleanup must first drop the call state — making
`is_current()` return `False`, which gates all result writes — then cancel,
unregister, and clear.

**Measured** (`churn_app.py`, 10 pages × 10 cycles × 5 mount/unmounts per
page = 500 mounts, macOS physical footprint): with the leak, idle climbs
`149 → 247 → 278 → 303 → 350 → 381 → ~390 MB` (peak 425 MB) and the first
sessions cost 27 MB each; with the unmount cleanup, idle stays flat at
~160–170 MB (peak 171 MB) and sessions cost ~0–2 MB at steady state. Same
workload, 2.4× the memory — and still climbing — versus a plateau.

**The general rules this adds**:

- Sub-session resources need their own churn test: create/destroy them many
  times *within* a live session (`churn_app.py` for the benchmark;
  a weakref mount/unmount test for the object level).
- Any registration in a long-lived registry (process-global lists,
  session-scoped callback lists) must be paired with deregistration at the
  registrant's *own* lifetime end — "the registry is cleaned at close" is
  only true for objects whose lifetime matches the registry's. A bound
  method in a callback list is a strong reference to the whole instance;
  register a `weakref.WeakMethod` when the callback is a courtesy rather
  than an ownership.

One more diagnosis trap found on the way (py3.11+): `gc.get_referrers` on a
coroutine's local shows the **coroutine object** as the referrer, not a
frame — so diagnosis code running inside a coroutine finds itself and cannot
be filtered by `f_code.co_name`. Put referrer-walking diagnosis in a
separate plain function and filter by its function names.

### Case study 3: the resurrection race in the fix, and the structural cure

The unmount cleanup above then produced its own leak — rarer, and only
visible as a flaky CI failure of the unmount test (one identical commit:
one run green, one run `2/6 payloads pinned` after 10 s of gc).

**The pattern — cleanup racing an in-flight writer**: the cleanup cleared
the kernel-store entries, but a worker thread that had already passed its
`is_current()` gate completed its result write *afterwards*, re-creating
the cleared entry with the payload inside — rooted until session close.
Check-then-act gates do not protect against writes already in flight when
the cleanup runs. A leak with this signature — *rare*, *never resolves
under repeated gc*, in code where cleanup clears storage that workers also
write — is a resurrection race. (The same hunt also surfaced a second
resurrector: reading an attribute through a lazy factory-backed accessor
(`Proxy → Singleton.get()`) after clearing re-created the entry too — know
your accessors' side effects before using them in cleanup.)

**How it was caught — make the flaky test self-diagnosing**: a leak that
reproduces once per N CI runs is not debugged by reading CI logs. Recipe:

1. Loop the exact failing configuration locally (`for i in $(seq 25); do
   pytest ...; done`). A pass that takes anomalously long (10.8 s vs 0.7 s)
   is the same bug barely resolving in time — count it as a hit.
2. Instrument the test itself: when the weakrefs are still alive past a
   threshold, dump the retainer chain (objgraph / referrer walk) *inside
   the test*, then keep going. The failure now names the retainer instead
   of just failing.
3. Crank the reproduction rate with contention: run several pytest
   processes in parallel — GIL churn widens every race window (4×30 runs
   caught what 60 sequential runs missed).

**The cure is structural, not a smarter cleanup** (solara #1186): the
race — and the flag+recheck machinery needed to win it, and the ordering
rules above — existed only because component-scoped state was stored in
kernel-scoped storage. Scoping the storage to its owner (the result lives
in a `SharedStore` *object* held by the component's hook state, as
`use_reactive` always did) made unmount cleanup happen by refcount, deleted
the cleanup code entirely, and turned the race harmless by construction: a
late write lands in an object that is already garbage and can pin nothing
beyond itself.

**The rule**: when state and its storage have different lifetimes, every
cleanup is a patch and every patch can race. Prefer storage whose lifetime
*is* the owner's lifetime (an object held by the owner) over shared
registries plus cleanup; reach for flip-flag-then-clear +
recheck-after-write only when restructuring is genuinely not an option.

### Case study 4: subscription residue — the leak every green assertion missed

Found in a large production solara app (July 2026) that leaked ~5 GB per
16 GB instance per business day while *all* of the checks above stayed green:
the cycle protocol showed only a small per-session cost locally, weakref
tests confirmed 0 kernel contexts and 0 render trees survived close, and
`/resourcez` counters returned to baseline every cycle. The production
dashboard disagreed with every lab result.

**Mechanism.** Every `ValueBase` (Reactive/Computed store) keeps per-scope
listener dicts: `listeners[scope_id]` / `listeners2[scope_id]`, with
`scope_id` = the kernel id for kernel-scoped subscriptions. Subscriptions
made through `use_effect` unsubscribe at close (rc.close() runs effect
cleanups). But `Computed`'s `AutoSubscribeContextManager` subscribes outside
any effect — and *even a module-level Computed subscribes per kernel*,
because its value is kernel-scoped. Nothing removes those entries at kernel
close. Each dead entry is a `(listener, Context)` tuple pinning the listener
closure and a `toestand.Context` (render-context + kernel-context refs) —
plus everything the closure captured. A `@solara.lab.computed` defined
*inside* a component body is the worst case: its closure captures the
component's locals (in the production app: the page's full dataset), leaked
once per render, forever. `Computed.__init__` also registers an
`on_kernel_start` reset in the process-global callback list and discards the
returned cleanup — a second permanent pin per runtime-created Computed.

**Why every check missed it:**

- The weakref assertions test *context/render-tree* survival. Dead listeners
  do not pin the context — the kernel closes fine; the leak is a separate
  closure graph hanging off process-lifetime stores. Green, and truthfully so.
- Per-session cost: at lab scale the leaked closures are a few KB — they
  disappeared into the accepted "allocator tail, decaying" reading. In
  production the closures captured MB-scale page data, and allocator
  fragmentation amplified the OS-level cost ~7× (2 MB/cycle of scattered
  Python survivors held ~14 MB/cycle of arenas hostage — the "keep 0.1%,
  return nothing" trap from the top of this document, live).

**The two detection rules this adds:**

1. **Counters, not just contexts: per-store listener totals must return to
   baseline every cycle.** Enumerate module-level stores via `sys.modules`
   (see `dump_module_store_listeners()` in
   [leak_canary_app.py](memory-measurement/leak_canary_app.py)) and compare
   scope/listener counts at every idle point. Any scope id that is not a
   live kernel is residue. This is a pure object-count check — it needs no
   memory measurement and catches the leak at natural (KB) scale.
2. **Amplify before you measure: give the suspect lifecycle a big payload.**
   The cycle protocol only sees what is large enough to clear the noise
   floor, so make the canary large: `leak_canary_app.py` captures a 1 MB
   payload *per render* in a component-scoped computed that reads a
   module-level reactive (and since the reactive is shared, every click
   re-renders every open page — each re-render leaks another captured
   payload). If subscription residue exists, the idle-point series grows by
   ~payload × renders per cycle — unmissable. (This generalizes the
   kitchen-sink 4.5 MB payload: put the payload *inside the specific
   closure/registration you suspect*, not just in kernel state.)

   **Measured** (solara 1.60.1, macOS physical footprint, 10 pages × 10
   cycles, 1 click/page): idle-point series
   `122 → 139 → 161 → 185 → 209 → 224 → 247 → 272 → 291 → 315 → 338 MB` —
   a constant ~22 MB/cycle line (≈ 1 MB × ~20 renders/cycle), while the
   harness reported `kernels after close: 0` on every single cycle. That is
   this leak class in one picture: the cleanup counters stay green and the
   process grows without bound. **With the fix** (per-kernel listener-scope
   purge at kernel close + kernel-scoped Singleton/Computed registrations):
   the same run stays flat at ~130–142 MB for all 10 cycles.

**Diagnosis traps found on the way** (each cost real time):

- **`gc.freeze` blinds the gc-based tools.** Production mode freezes startup
  objects; frozen objects are invisible to `gc.get_objects()` and are not
  reported by `gc.get_referrers()` — every referrer chain from a leaked
  object dead-ended at "no referrers" because the holder (a module-level
  store) was frozen, and `objgraph.find_backref_chain` found no path to any
  module. For diagnosis, call `gc.unfreeze()` first (diagnosis process only)
  — but expect the next trap.
- **objgraph backref search does not scale past unfreeze**: BFS over ~850k
  newly-visible objects is effectively O(N²) via repeated `get_referrers`
  scans; it pinned a CPU for hours. Prefer scope-targeted counters (rule 1)
  over generic backref walking on big heaps.
- **Never `getattr`-sweep live objects.** A scan doing
  `getattr(obj, "listeners", None)` over `gc.get_objects()` wedged the
  server: proxy objects run arbitrary `__getattr__` (lock-taking, kernel
  context access). Use `obj.__dict__.get(...)` or
  `inspect.getattr_static`.
- **Error paths that `repr` framework objects can be their own incident**:
  one "could not close render context" log line embedded the full kernel
  context repr — megabytes per line, 12 MB of log in one test run.

**Fix guidance** (for solara itself, and for any framework with per-scope
subscriptions on process-lifetime objects): purge a store's
`listeners[scope_id]` entries when the *scope* dies (kernel close for
kernel scopes). Two traps make the naive fix wrong: (1) session-scoped
stores (`persist=True`) share one scope across all of a session's kernels —
purging on kernel close breaks live sibling kernels; only purge scopes that
die with the kernel. (2) close-ordering: `on_close` callbacks run before the
render context's effect cleanups, so cleanups must tolerate
already-removed entries (discard semantics), or the purge must run after
teardown — a raising cleanup aborts the whole render-context close.

**Epilogue: the fix itself raced — twice.** With the owner cleanup shipped,
a 25-cycle run of the same production app still leaked a constant
~10 MB/cycle. The counters (not the memory numbers) named it: after gc with
zero kernels, one surviving `AutoSubscribeContextManager` per (Computed,
kernel) and their listener entries were back. Two lessons in reading that
census:

- **Subclass discrimination**: the Reacton (component) managers counted 0 —
  their effect-cleanup path works — all survivors were the plain (Computed)
  kind. One count split the search space in half.
- **Per-owner arithmetic**: survivors ≈ instances × kernels means the
  cleanup *ran and was undone*, not skipped. "Undone after it ran" has
  exactly two shapes, both already in case study 3: a **write race** (a
  recompute in a task thread re-subscribed between `unsubscribe_all` and
  kernel death — fix: flip-flag-then-clear, and re-check the flag after the
  subscribing write, undoing your own write if you lost) and **lazy-factory
  resurrection** (a post-close `computed.value` access re-created a *fresh*
  manager whose `on_close` registration landed on an already-closed context
  and never ran — fix: `on_close` on a closed context runs the callback
  immediately, so late-created resources are born closed). The first fix
  halved the residue; the arithmetic on what remained pointed straight at
  the second.

The meta-rule: when a leak you fixed comes back at a rate proportional to
(owners × scopes), do not re-diagnose from scratch — check the two
resurrection shapes first, and write each as a deterministic
fails-on-master test before fixing.

### Leak or retention? The shape answers it

Linux `anon` at the idle point of each click-app cycle:
`95.8 → 101.7 → 105.4 → 106.9 → 107.5 → 107.8 → 108.0 → 108.2 → 108.9 → 109.1 → 109.2 MB`.
The increments decay (+5.9, +3.7, +1.5, +0.6, … +0.1): an asymptotic
plateau — allocator/pool warmup, **not** a leak. A leak adds a constant
amount per cycle. Also measured: memory allocated while 10 kernels are open
is *not* returned to the OS on cull (pymalloc/glibc retention), but the next
cycle *reuses* it — that is why the steady-state per-kernel delta is almost
zero, and why "RSS didn't go down after the user left" is not, by itself, a
leak.

The same run on macOS told the same story only in the physical footprint
(119.5 → 124.6 MB, decaying); RSS bounced 70–142 MB with no correlation to
load at all.

### Cleanup correctness

Across all runs (400+ kernel lifecycles), after every cycle `/resourcez`
reported kernels = 0, websockets open = 0 (attempts == closed), threads back
to baseline; culls completed in 1–2 s with `SOLARA_KERNEL_CULL_TIMEOUT=0.5s`.
At the object level, `tests/integration/memleak_test.py` (weakref assertions
on context/kernel/shell/session) passed 10/10 repeated runs on both flask and
starlette.

## Solara specifics

- **`/resourcez`** (JSON): kernel counts (total/connected/disconnected),
  websocket counts (attempts/connecting/open/closed), thread counts, state
  backend health. `?verbose=1` adds CPU and memory — note the memory block is
  `psutil.virtual_memory()`, i.e. **the whole machine**, not the solara
  process. Use the counters as cleanup ground truth; get process memory from
  the OS tools above.
- `SOLARA_KERNEL_CULL_TIMEOUT` — kernel cleanup delay after disconnect
  (default 24h; set `0.5s` in measurement runs).
- `SOLARA_KERNELS_MAX_COUNT` — hard cap on kernels, prevents unbounded growth.
- `SOLARA_GC_FREEZE` — `gc.freeze()` the startup state (imports, module-level
  app state) after the app first ran in the dummy kernel, moving it out of
  every later gc pass. Default: on in production mode, off in development
  (hot reload would freeze stale app modules into a permanent leak).
  **Measured** (1-CPU docker, ~250 MB module-level baseline, full collection
  after every kernel close via `gc_after_close`): mean gen-2 pause 75.8 ms →
  4.8 ms (16×), median 69.7 → 2.5 ms. The bigger the import baseline (torch,
  pandas), the bigger the win: gc cost becomes proportional to live session
  state instead of process size. Harness: `measure_gc_freeze.py` +
  `gc_freeze_bench_app.py`. Not a leak fix — purely gc-pause cost.
- Per-user state lives in the virtual kernel; per-kernel cost is dominated by
  your app's state, not the framework (~0.6 MB floor, see baselines).

## Checklist for agents

Executing a "measure memory / find the leak" task, in order:

1. **Define the workload cycle** first: open N sessions → use them → close →
   confirmed cleanup. No cycle, no conclusion.
2. **Pick the metric for the platform**: Linux cgroup `anon` > macOS
   `vmmap` footprint > Linux RSS. Never macOS RSS trends.
3. **Warm up one cycle** before measuring anything.
4. **Run ≥ 10 cycles**, record idle/loaded/idle per cycle plus the app's own
   cleanup counters.
5. **Judge by shape**: decaying increments = retention (healthy plateau);
   constant increments = leak (report MB/cycle); counters not returning to
   baseline = cleanup bug, fix before memory analysis.
5b. **Run the churn variant too**: repeatedly create/destroy sub-resources
   *inside* live sessions (component mount/unmount). The session cycle is
   blind to per-mount accumulation — it freed everything at close before you
   could see it (this hid a real `use_task` leak; see the case study).
5c. **Check registry/subscription residue too**: per-store listener totals
   (and any per-scope registry) must return to baseline every cycle —
   context/render-tree weakrefs stay green while dead listener entries on
   module-level stores pin arbitrary captured data (case study 4;
   `dump_module_store_listeners()` in leak_canary_app.py). If a leak is
   suspected but below the noise floor, amplify it: put a multi-MB payload
   inside the specific closure/registration lifecycle you suspect.
6. **If leak**: `memray flamegraph --leaks` (with `PYTHONMALLOC=malloc`) for
   *what allocated it*; weakref + objgraph per
   [memory-leak-detection.md](memory-leak-detection.md) for *why it is alive*.
6b. **If the leak is flaky** (one CI run in N; a rare test pass that takes
   10× longer is the same hit): make the test self-diagnosing — dump the
   retainer chain inside the test when weakrefs survive past a threshold —
   and crank reproduction with parallel pytest processes (GIL contention
   widens race windows). Rare + never-resolving-under-gc + cleanup that
   clears storage workers also write = a resurrection race (case study 3).
7. **If overuse (no leak, just big)**: memray flamegraph at peak for
   attribution; tracemalloc diff for Python-level growth; remember imports
   are a fixed ~tens-of-MB baseline.
8. **For capacity questions**: run in a memory-limited docker container and
   read `memory.peak` / `anon`, not profilers.
9. **Report** numbers with their metric and platform ("109 MB cgroup anon,
   Linux"), the curve shape, and the counter evidence — not bare "RSS was X".

Known traps, all measured: macOS RSS compressor noise; `memory.current`
page-cache pollution; USS needs root on macOS; `ru_maxrss` bytes-vs-KB;
`_debugmallocstats` writes to C stderr; `memray tree` is interactive;
tracemalloc sees numpy but not raw native malloc; a busy port means you may be
measuring (or clicking!) someone else's server — assert the pid you measure
is the one you started; a sawtooth curve (rise + periodic sharp drops) is
gen-2 GC lag on reference cycles, not a leak; exception tracebacks pin every
frame they passed through (strip `__traceback__` before storing exceptions);
log-capture handlers in test harnesses retain those tracebacks and turn them
into phantom flaky leaks — clear captured records inside the GC loop;
cleanup that clears shared storage races in-flight writers (resurrection —
case study 3), and lazy factory-backed accessors re-create what you just
cleared — prefer storage scoped to the owner's lifetime over cleanup code;
`gc.freeze` (production default) hides frozen holders from `gc.get_objects`
and `gc.get_referrers` — referrer chains dead-end at module-level stores
unless you `gc.unfreeze()` first (diagnosis only); never `getattr`-sweep
live objects (proxy `__getattr__` side effects wedge servers — use
`__dict__.get`/`inspect.getattr_static`); objgraph backref BFS is unusable
on ~1M-object heaps — use scope-targeted counters instead (case study 4).

## Which tool for which question

| Question | Tool |
|----------|------|
| How much memory does the process use right now? | Linux: `psutil` RSS/USS; macOS: `vmmap -summary <pid>` physical footprint (RSS is compressor noise) |
| What was the peak? | `resource.getrusage(...).ru_maxrss` (mind the Linux/macOS unit trap), or cgroup `memory.peak` |
| Is Python holding freed memory in its arenas? | `sys._debugmallocstats()` |
| Which Python code allocated the growth? | `tracemalloc` snapshot diff |
| Which code (incl. C extensions) owns the memory? | `memray flamegraph`, `--native` |
| What was allocated and never freed? | `memray flamegraph --leaks` with `PYTHONMALLOC=malloc` |
| Why is this object still alive? | `objgraph` — see [memory-leak-detection.md](memory-leak-detection.md) |
| Which types dominate the heap? | `objgraph.most_common_types()` / `gc.get_objects()` counter |
| Will it fit in a 512 MB pod under load? | docker `--memory` + cgroup `memory.peak` / `anon` |
| Did the sessions actually get cleaned up? | the app's counter endpoint (Solara: `/resourcez`) |
| Is this growth a leak or retention? | idle-point series over ≥10 cycles: line = leak, plateau = retention |
