# Memory Leak Detection in Solara

This document describes how Solara detects and prevents memory leaks, aimed at helping LLMs (and humans) understand the patterns and apply them when writing new code or tests.

## Core Concept: Weakref-Based Leak Detection

The fundamental technique is:

1. **Create a weak reference** to an object that *should* be garbage collected.
2. **Remove all strong references** to that object (close contexts, navigate away, delete locals, exit scopes).
3. **Force garbage collection** across all generations.
4. **Assert the weakref resolves to `None`** — if it doesn't, something is still holding a strong reference, and you have a leak.

```python
import gc
import weakref

obj = SomeExpensiveObject()
ref = weakref.ref(obj)

# Remove the only strong reference
del obj

gc.collect()
assert ref() is None, "Leak detected: something still references the object"
```

A `weakref.ref` does **not** prevent garbage collection. If the weakref still resolves to a live object after you've removed all *intended* references and forced GC, there is an unintended reference keeping it alive — that's a memory leak.

## How Solara Tests for Memory Leaks

The primary test lives in `tests/integration/memleak_test.py`. It tests that closing a browser page properly cleans up the entire kernel context and all associated objects.

### Step-by-step walkthrough

#### 1. Set up weak references to critical objects

```python
# Get the kernel context created for this page
context = weakref.ref(list(solara.server.kernel_context.contexts.values())[0])

ctx = context()
kernel = weakref.ref(ctx.kernel)
krn = kernel()
shell = weakref.ref(krn.shell)
session = weakref.ref(krn.session)
```

These four weakrefs track the full lifecycle chain: context → kernel → shell/session. If any of them survive after cleanup, there is a leak.

#### 2. Trigger cleanup by navigating away

```python
page_session.goto("about:blank")
```

When the browser navigates away, the server detects the disconnect and starts culling the kernel. The test uses a `no_cull_timeout` fixture that sets `SOLARA_KERNEL_CULL_TIMEOUT` to near-zero so cleanup happens immediately.

#### 3. Wait for cleanup to complete

```python
# Wait for the kernel cull task to finish
if last_cull_task is not None and not last_cull_task.done():
    event = threading.Event()
    last_cull_task.add_done_callback(lambda _: event.set())
    assert event.wait()

# Wait for the context's close() method to finish
closed_event = ctx.closed_event
assert closed_event.wait(10)
```

The `VirtualKernelContext` has a `closed_event` (a `threading.Event`) that gets set at the very end of its `close()` method. This is the synchronization point that tells the test "cleanup is done, you can now check for leaks."

#### 4. Break local references

```python
del ctx, krn, last_cull_task, closed_event
if shell():
    del shell().__dict__
```

The test **must** delete its own local variables that hold strong references to the objects being tested. Without this, the test itself would keep objects alive.

The `del shell().__dict__` is a workaround for IPython's shell holding internal references that prevent collection.

#### 5. Use a scoped function to ensure locals are truly gone

```python
def _scoped_test_memleak(page_session, solara_server, solara_app, extra_include_path):
    # ... all the setup from steps 1-4 ...
    return context, kernel, shell, session

def test_memleak(...):
    context_ref, kernel_ref, shell_ref, session_ref = _scoped_test_memleak(...)
```

By putting the setup in a separate function, all local variables (`ctx`, `krn`, etc.) go out of scope when the function returns. The test function only receives the weakrefs. This is critical — in Python, `del` removes the *name binding* but doesn't guarantee the object is freed if the frame still exists. Returning from a function destroys the entire frame.

#### 6. Clear external reference holders

```python
# Playwright tracing holds references to coroutines executed in the scoped function
page_session.context.tracing.stop()
```

Third-party libraries can hold unexpected references. Playwright's tracing keeps references to coroutines, which in turn reference local variables from the scoped function. Stopping the trace clears those references.

#### 7. Aggressive garbage collection

```python
for i in range(200):
    time.sleep(0.1)
    for gen in [2, 1, 0]:
        gc.collect(gen)
    if context_ref() is None and kernel_ref() is None and shell_ref() is None and session_ref() is None:
        break
```

The test runs up to 200 rounds of garbage collection across all three generations. It collects generation 2 first (oldest), then 1, then 0 (youngest). The `time.sleep(0.1)` gives background threads time to release their references (e.g., asyncio tasks finishing, thread-local storage being cleaned up).

The early-exit check avoids waiting the full 20 seconds when objects are collected quickly.

#### 8. Diagnose failures with objgraph

```python
else:
    refs_to_show = [ref() for ref in [context_ref, kernel_ref, shell_ref, session_ref] if ref() is not None]
    output_path = Path(...) / f"mem-leak-{name}-python-{sys.version_info}.pdf"
    objgraph.show_backrefs(refs_to_show, filename=str(output_path), max_depth=15)
```

When the test fails, it uses `objgraph.show_backrefs()` to generate a PDF showing the chain of references keeping the object alive. This is the most valuable debugging artifact — it shows exactly *who* is holding the reference. The PDF is saved as a CI artifact for later inspection.

#### 9. Assert everything is collected

```python
assert context_ref() is None
assert kernel_ref() is None
assert shell_ref() is None
assert session_ref() is None
```

## Leak Prevention Patterns in Production Code

### Use weakrefs for back-references and callbacks

When object A owns object B, but B needs to reference A (e.g., for callbacks), B should hold a `weakref` to A. Otherwise you get a reference cycle that may not be collected promptly — or at all if the cycle involves objects with `__del__` methods.

**Example from `solara/tasks.py`:**

```python
class TaskAsyncio(Task):
    _context: Optional["weakref.ReferenceType[VirtualKernelContext]"] = None

    def __call__(self, *args, **kwargs):
        context = solara.server.kernel_context.get_current_context()
        self._context = weakref.ref(context)  # weak! doesn't prevent context GC
```

The task needs the context to check if it's still alive, but must not *prevent* the context from being garbage collected when the user disconnects.

**Example from `solara/server/app.py`:**

```python
comm_ref = weakref.ref(comm)
del comm
```

The reload handler stores a weakref to the comm object so it doesn't pin the entire communication channel in memory.

### Explicit cleanup in `close()` methods

The `VirtualKernelContext.close()` method (in `solara/server/kernel_context.py`) follows a thorough cleanup sequence:

1. Run registered `_on_close_callbacks` in reverse order (LIFO — like a stack of destructors)
2. Close the reacton render context (which closes all rendered components)
3. Close all widgets via `widgets.Widget.close_all()`
4. Close the kernel and set `self.kernel = None` (breaks the strong reference)
5. Remove from the global `contexts` dict
6. Remove from thread-local `current_context` — including stale `_DummyThread` entries that may reference this context
7. Signal `closed_event` to notify waiters

Setting attributes to `None` after closing them is a deliberate pattern to break reference cycles. Without `self.kernel = None`, the context would still hold a strong reference to the kernel even after it's "closed."

### Avoid hidden references in shell/IPython internals

The custom `SolaraInteractiveShell` (in `solara/server/shell.py`) disables several IPython features that cause memory leaks:

```python
def init_sys_modules(self):
    pass  # don't create a __main__, it will cause a mem leak

def init_prefilter(self):
    pass  # avoid consuming memory

def init_history(self):
    self.history_manager = Mock()  # don't accumulate history

def reset(self, new_session=True, aggressive=False):
    pass  # IPython's reset() calls gc.collect() which causes slow shutdowns
```

### Clean up thread-local references to dead contexts

```python
# In VirtualKernelContext.close():
_contexts = current_context.copy()
for key, _ctx in _contexts.items():
    if _ctx is self:
        del current_context[key]
```

Python's `threading.local()` and `_DummyThread` objects can hold stale references to kernel contexts. The close method proactively scans and removes these.

## Writing New Leak Tests

When adding a new feature that manages resources (widgets, connections, tasks, caches), consider adding a leak test. Here's the template:

```python
import gc
import weakref

def test_my_feature_does_not_leak():
    # 1. Create the object
    obj = create_my_object()
    ref = weakref.ref(obj)

    # 2. Use it
    obj.do_something()

    # 3. Clean it up through the normal lifecycle
    obj.close()  # or however it's supposed to be cleaned up

    # 4. Remove local reference
    del obj

    # 5. Collect garbage
    gc.collect()

    # 6. Assert it's gone
    assert ref() is None, f"Leak: {ref()} is still alive"
```

### Tips

- **Scope your setup in a helper function** and only return weakrefs. This ensures Python frame locals don't accidentally keep objects alive.
- **Delete `__dict__`** on objects whose internal state creates reference cycles (common with IPython shells).
- **Check third-party library state** — frameworks like Playwright, asyncio, and IPython can hold references in unexpected places (traces, task results, history).
- **Use `objgraph.find_backref_chain()` first** — this is the single most effective diagnostic. It finds the shortest path from your leaked object to a root (module-level) object, which directly shows you the retention chain. Manual `gc.get_referrers()` traversal is noisy and often leads to dead ends. See the "Debugging Strategy" section below.
- **Run GC multiple times** — some cycles require multiple passes. The existing test runs up to 200 rounds across all 3 generations.
- **Add `time.sleep()` in GC loops** if background threads might be holding references that will be released shortly (e.g., async tasks completing, thread-local cleanup).
- **Use `closed_event` or similar synchronization** to ensure cleanup has actually finished before checking weakrefs.
- **Watch out for closures** — a lambda or nested function that captures a variable in its closure keeps that variable alive. This is a common source of leaks in callback-heavy code.
- **Watch out for saved/restored state** — context managers that save state in `__enter__` and restore it in `__exit__` can leak if they don't clear the saved attribute after restoring it. The saved value may reference objects that should be freed.
- **Bound methods are implicit references** — `self.method` creates a bound method object that holds a reference to `self`. Storing a bound method anywhere (attribute, list, dict, closure) transitively keeps `self` and everything it references alive.
- **Check which file Python actually imports** — if a package is installed (not editable), the venv has its own copy at `.venv/lib/pythonX.Y/site-packages/`. Editing the source repo won't affect tests unless installed in editable mode. Verify with: `python -c "import module; print(module.__file__)"`.
- **Test from simple to complex** — start with `sl.Text()`, then add complexity. When the first test fails, the component that introduced the leak is the differentiator. This narrows the search space dramatically.

### Debugging Strategy: How to Find the Retention Chain

When a leak is detected, follow this order:

#### 1. Use `objgraph.find_backref_chain()` (best first step)

```python
import objgraph

# Find shortest path from leaked object to any module (a "root" in Python's GC sense)
chain = objgraph.find_backref_chain(leaked_obj, objgraph.is_proper_module, max_depth=20)
for i, item in enumerate(chain):
    type_name = type(item).__name__
    if hasattr(item, '__name__'):
        type_name += f" ({item.__name__})"
    print(f"  [{i:2d}] {type_name}")
```

This typically reveals the full chain in one call. The output reads top-to-bottom as: "the module holds a dict, which holds X, which holds Y, ... which holds the leaked object."

#### 2. Generate a visual graph for complex cases

```python
objgraph.show_backrefs([leaked_obj], filename="leak.pdf", max_depth=15)
```

Useful when there are multiple retention paths or the chain involves cycles.

#### 3. Avoid raw `gc.get_referrers()` traversal

Manual BFS/DFS over `gc.get_referrers()` produces overwhelming output — lists of lists of list_iterators of tuples of cells. It's easy to get lost and follow irrelevant chains. Only use it for spot-checks on specific objects after `objgraph` has pointed you in the right direction.

#### 4. Traps to avoid

- **`hasattr(type(obj), '__del__')` gives false positives** — built-in types like `cell`, `list`, `list_iterator` report having `__del__` but this is not the Python-level `__del__` method. On Python 3.4+, `__del__` in cycles is not a problem anyway (PEP 442).
- **"External root" analysis is too noisy** — trying to find which objects in a referrer cluster have references from outside the cluster sounds smart but produces hundreds of false positives because the cluster boundary is hard to define.
- **The first obvious suspect may not be the real cause** — the `Context` class holding a strong `render_context` reference looked like the culprit, but the actual root cause was `previous_reactive_watch` on a different object. Always verify with `objgraph` before committing to a fix.

### Common leak sources in Solara

| Source | Why it leaks | Fix |
|--------|-------------|-----|
| Global dicts (`contexts`, `current_context`) | Strong reference prevents GC | Remove entry in `close()` |
| Thread-local storage | `_DummyThread` entries outlive the context | Scan and remove in `close()` |
| IPython `__main__` module | Module objects are rarely collected | Don't create it (`init_sys_modules = pass`) |
| Callbacks/closures capturing `self` | Closure keeps `self` alive | Use `weakref.ref(self)` in the closure |
| Asyncio tasks referencing context | Task keeps context alive until it finishes | Store `weakref.ref(context)` instead |
| Comm objects for reload | Comm pins the context | Store as `weakref.ref(comm)` |
| Playwright tracing | Traces hold coroutine frames | Stop tracing before asserting |
| Context manager saved state (`previous_X`) | `__enter__` saves a ref, `__exit__` restores but doesn't clear | Set `self.previous_X = None` after restoring |
| Bound methods stored on long-lived objects | Bound method holds `self` transitively | Clear the attribute or use a weakref |
| `@slab.computed` / `Computed` auto-subscriptions | Module-level Singleton retains per-render references | Clear saved state in `__exit__`, use weakrefs in Context |

## Tools

- **`weakref`** (stdlib) — create references that don't prevent garbage collection
- **`gc`** (stdlib) — force garbage collection, inspect referrers (`gc.get_referrers(obj)`)
- **`objgraph`** (third-party, dev dependency) — **the most useful tool for leak debugging**. Key functions:
  - `find_backref_chain(obj, predicate)` — finds shortest path from obj to a root. Use `objgraph.is_proper_module` as predicate.
  - `show_backrefs([obj], filename="leak.pdf")` — generates a visual reference graph as PDF
  - `count(typename)` — count live instances of a type
- **`sys.getrefcount()`** (stdlib) — check how many references exist to an object (note: the call itself adds one)

## Configuration

- `SOLARA_KERNEL_CULL_TIMEOUT` — how long to wait before cleaning up a disconnected kernel (default: 24h, set to near-zero in tests)
- `SOLARA_KERNELS_MAX_COUNT` — maximum number of kernels allowed (prevents unbounded memory growth)
- `/resourcez` endpoint — runtime memory stats (add `?verbose` for details)
