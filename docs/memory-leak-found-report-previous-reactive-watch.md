# Memory Leak Report: `previous_reactive_watch` Retains Render Context

## Summary

`AutoSubscribeContextManagerBase.__exit__()` restores `thread_local.reactive_watch` from `self.previous_reactive_watch` but never clears the attribute afterwards. When a `Computed` (created by `@slab.computed`) is evaluated during a component render, its `AutoSubscribeContextManager` stores a bound method from the component's `AutoSubscribeContextManagerReacton` in `self.previous_reactive_watch`. Since `Computed` is module-level and the `AutoSubscribeContextManager` lives in a per-kernel `Singleton`, this reference persists indefinitely, transitively pinning the `_RenderContext` through closure cells.

## Affected Components

Any component that reads a `@slab.computed` value. In the copilot app, the `Objections` component reads `extract.needs_attention_objection` (a `@slab.computed`), and the full `Page` component reads multiple computed values transitively.

## Fix

Two lines added to `AutoSubscribeContextManagerBase.__exit__()` in `solara/toestand.py`:

```python
def __exit__(self, exc_type, exc_val, exc_tb):
    thread_local.reactive_used = self.reactive_used_before
    thread_local.reactive_watch = self.previous_reactive_watch
    # NEW: clear saved references to avoid preventing garbage collection
    self.previous_reactive_watch = None
    self.reactive_used_before = None
    self.unsubscribe_previous()
    self.subscribed_previous_run = self.subscribed.copy()
```

A secondary defense-in-depth change makes `Context` use `weakref.ref` for its `render_context`, so even if other retention paths exist, the `Context` objects stored in `listeners`/`listeners2` dicts cannot pin a `_RenderContext`.

## Reference Chain (from objgraph)

```
module (copilot.state.extract)
  -> dict['needs_attention_objection']
    -> Computed
      -> Singleton
        -> KernelStoreFactory
          -> dict['solara.toestand:AutoSubscribeContextManager:5']
            -> AutoSubscribeContextManager
              -> self.previous_reactive_watch = method (add)
                -> AutoSubscribeContextManagerReacton
                  -> self.on_change = function (force_update)
                    -> closure tuple -> cell -> function (set_counter)
                      -> closure tuple -> cell -> _RenderContext  <-- LEAKED
```

## How the Leak Happens: Step by Step

1. Component renders. `AutoSubscribeContextManagerReacton.__enter__()` sets `thread_local.reactive_watch = self.add` (a bound method on the component's auto-subscriber).

2. Component reads `needs_attention_objection.value` (a `@slab.computed`).

3. The `Computed`'s `KernelStoreFactory` evaluates its factory function, which enters the `Computed`'s own `AutoSubscribeContextManager.__enter__()`.

4. In `__enter__()`, the context manager saves the current thread-local watch:
   ```python
   self.previous_reactive_watch = thread_local.reactive_watch
   # This is now AutoSubscribeContextManagerReacton.add — a bound method
   ```

5. The factory function runs, subscribes to dependencies, then `__exit__()` runs.

6. `__exit__()` restores `thread_local.reactive_watch = self.previous_reactive_watch` but **never clears** `self.previous_reactive_watch`.

7. The `AutoSubscribeContextManager` lives in a `Singleton` on the module-level `Computed` object. So `self.previous_reactive_watch` persists across the entire kernel lifetime.

8. The bound method `AutoSubscribeContextManagerReacton.add` holds its `self` (the `AutoSubscribeContextManagerReacton` instance), which holds `self.on_change = force_update`, which is a closure capturing `set_counter` (from `solara.use_state`), which is a closure capturing the `_RenderContext` through closure cells.

9. When the render context closes, the `_RenderContext.close()` cleans up component effects (which calls `AutoSubscribeContextManagerReacton.unsubscribe_all()`), but the `AutoSubscribeContextManager` on the `Computed`/`Singleton` still holds the stale `previous_reactive_watch` reference.

10. The `_RenderContext` cannot be garbage collected because the module-level `Computed` -> `Singleton` -> `AutoSubscribeContextManager` -> `previous_reactive_watch` chain is rooted in a module-level object that is never collected.

## Investigation Process and Analysis Strategy

This section documents the approach taken, including dead ends, so future investigators can work more efficiently.

### Phase 1: Build test infrastructure

Created a weakref-based test harness (see `memory-leak-strategy-render-context-weakref.md`) and wrote tests from simple to complex:

1. Baseline: `sl.Text`, `sl.Column`, `sl.Markdown` — validate the harness works
2. Simple components: `PKBUserSelectedBuilding`, `SkeletonLoader`
3. Stateful: `ClientHeader` (reads `sl.reactive` values directly)
4. Complex: `Objections` (reads `@slab.computed` values)
5. Full app: `Page` (everything)

Tests 1-3 passed. Test 4 leaked. This immediately narrowed the problem to something specific about `@slab.computed` that plain `sl.reactive` doesn't trigger.

### Phase 2: Initial hypothesis (wrong)

First hypothesis: the `Context` class in `subscribe_change()` holds a strong reference to `_RenderContext`. This seemed like the obvious culprit because `AutoSubscribeContextManager` (used by `Computed`) doesn't register `use_effect()` cleanup, unlike `AutoSubscribeContextManagerReacton`.

Applied a weakref fix to `Context.render_context`. **The leak persisted.** This was a red herring — or rather, it's a valid defense-in-depth fix, but not the primary retention path.

### Phase 3: objgraph reveals the real chain

The breakthrough was using `objgraph.find_backref_chain()`:

```python
import objgraph
chain = objgraph.find_backref_chain(rc_ref(), objgraph.is_proper_module, max_depth=20)
for i, item in enumerate(chain):
    type_name = type(item).__name__
    if hasattr(item, '__name__'):
        type_name += f" ({item.__name__})"
    print(f"  [{i:2d}] {type_name}")
```

This immediately showed the chain from the module-level `Computed` through `Singleton` → `AutoSubscribeContextManager` → `method (add)` → `AutoSubscribeContextManagerReacton` → closures → `_RenderContext`.

The key insight was that `method (add)` is a **bound method** of `AutoSubscribeContextManagerReacton`, stored as `previous_reactive_watch` on the `AutoSubscribeContextManager`. This was not visible from reading the code alone — the reference is implicit because Python bound methods hold a reference to their `self`.

### Phase 4: Verify and fix

Reading `__enter__`/`__exit__` with the objgraph output in hand made the bug obvious: `previous_reactive_watch` is set in `__enter__` but never cleared in `__exit__`. Two-line fix, verified by running all 8 memleak tests (all pass) and all 27 previously-passing Solara toestand unit tests (no regressions).

### What Worked

- **Incremental test complexity** — testing from `sl.Text` up to `Page` let us immediately pinpoint that `@slab.computed` was the differentiator.
- **`objgraph.find_backref_chain(obj, objgraph.is_proper_module)`** — this single call revealed the entire retention chain in one shot. Much more efficient than manual `gc.get_referrers()` traversal.
- **Testing the fix on the installed site-packages** — the Solara source repo and the venv's installed copy are separate files. Editing only the source repo doesn't affect tests that import from the venv.

### What Didn't Work / Traps

- **Manual `gc.get_referrers()` traversal** — produces overwhelming output with lists, tuples, dicts, list_iterators, and cells. Very hard to follow without objgraph's path-finding. The BFS approach (finding all objects in the referrer cluster, then identifying external roots) was too noisy — 306 objects out of 501 had "external references" because the cluster was too broadly defined.
- **Checking for `__del__` methods** — seemed relevant (objects with `__del__` in cycles can't be collected in Python < 3.4), but on Python 3.12 this is a non-issue (PEP 442). Also, `hasattr(type(obj), '__del__')` produces false positives on built-in types like `cell`, `list`, `list_iterator`.
- **Assuming the `Context` class was the only retention path** — the `Context` weakref fix was necessary but not sufficient. There were two independent paths keeping `_RenderContext` alive: (1) `Context.render_context` in listener dicts, and (2) `previous_reactive_watch` on the `AutoSubscribeContextManager`. Only objgraph revealed path (2).
- **Editing only the Solara source repo** — if Solara is installed as a regular package (not editable), the venv has its own copy at `.venv/lib/pythonX.Y/site-packages/solara/toestand.py`. Always check which file Python actually imports: `python -c "import solara.toestand; print(solara.toestand.__file__)"`.

## How to Reproduce

```python
import gc, uuid, weakref
import solara
import solara.server.kernel
import solara.server.kernel_context

def _scoped_render(component_el):
    widget, rc = solara.render_fixed(component_el, handle_error=False)
    rc_ref = weakref.ref(rc)
    rc.close()
    del widget, rc
    return rc_ref

kernel = solara.server.kernel.Kernel()
kc = solara.server.kernel_context.VirtualKernelContext(
    id=str(uuid.uuid4()), kernel=kernel, session_id="s1"
)
with kc:
    # Any component that reads a @slab.computed value
    from your_app import ComponentThatReadsComputed
    rc_ref = _scoped_render(ComponentThatReadsComputed())
    for _ in range(20):
        gc.collect()
    assert rc_ref() is None, "Leak!"
```

## Files Changed

- `solara/toestand.py` — `AutoSubscribeContextManagerBase.__exit__()`: clear `previous_reactive_watch` and `reactive_used_before` after restoring them
- `solara/toestand.py` — `Context.__init__()`: use `weakref.ref` for `render_context` (defense-in-depth)

## Test Coverage

- `tests/memleak/test_memleak_copilot.py` — 8 tests covering `sl.Text`, `sl.Column`, `sl.Markdown`, `PKBUserSelectedBuilding`, `SkeletonLoader`, `ClientHeader`, `Objections` (reads `@slab.computed`), and full `Page`
- All 27 previously-passing Solara `toestand_test.py` unit tests continue to pass
