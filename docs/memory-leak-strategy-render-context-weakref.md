# Strategy: Render Context Weakref Leak Detection

## Goal

Detect memory leaks in Solara components by verifying that a component's render context is garbage-collected after cleanup.

## When to use

Use this strategy when you want to verify that a Solara component (or a change to one) does not leak memory. It works at the unit-test level — no server, no browser, no kernel context required.

## Core idea

1. Render a component with `solara.render_fixed()`.
2. Take a `weakref.ref` to the `_RenderContext` returned by `render_fixed`.
3. Close the render context and delete all local strong references.
4. Force garbage collection.
5. If the weakref still resolves to a live object, something is holding an unintended strong reference — that's a leak.

The render context is the right object to track. If it leaks, the entire component tree and all its state leak with it. Widgets (ipyvue `Html` nodes) have internal bound methods that keep them alive independently of the render context — that is normal and handled by `Widget.close_all()` during the full kernel lifecycle.

## Key technique: scoped function

All setup must happen inside a **separate function** that returns only the weakref. This ensures Python destroys the function's local variables (which hold strong references to the render context and widget) when the frame exits. Without this, `del` on locals is not enough — the frame object itself can keep them alive.

```python
def _scoped_render(component_el):
    widget, rc = solara.render_fixed(component_el, handle_error=False)
    rc_ref = weakref.ref(rc)
    rc.close()
    del widget, rc
    return rc_ref
```

## Template

```python
import gc
import weakref
import solara


def _scoped_render(component_el):
    """Render inside a function so all locals die when we return."""
    widget, rc = solara.render_fixed(component_el, handle_error=False)
    rc_ref = weakref.ref(rc)
    rc.close()
    del widget, rc
    return rc_ref


def check_leak(name: str, component_el) -> bool:
    """Returns True if a leak is detected."""
    rc_ref = _scoped_render(component_el)

    for _ in range(20):
        for gen in [2, 1, 0]:
            gc.collect(gen)
        if rc_ref() is None:
            break

    rc_alive = rc_ref() is not None

    if rc_alive:
        print(f"[LEAK]  {name}: render context is still alive!")
        obj = rc_ref()
        if obj is not None:
            referrers = gc.get_referrers(obj)
            print(f"        render context has {len(referrers)} referrer(s):")
            for r in referrers[:5]:
                print(f"          - {type(r).__name__}: {repr(r)[:120]}")
        return True
    else:
        print(f"[OK]    {name}: render context collected — no leak")
        return False
```

## Proven baseline

This strategy was validated with two components: one clean, one intentionally leaky. The leaky component stores a `use_state` setter in a global list, which creates a reference chain (global list -> setter closure -> component state -> render context) that prevents collection.

### Leaky component (should be caught)

```python
_leaked_references: list = []

@solara.component
def LeakyComponent():
    text, set_text = solara.use_state("hello")
    _leaked_references.append(set_text)  # BUG: global reference
    solara.Text(text)
```

### Clean component (should pass)

```python
@solara.component
def CleanComponent():
    text, set_text = solara.use_state("hello")
    solara.Text(text)
```

### Actual output

```
============================================================
Memory Leak Detection Demo
============================================================

--- Test 1: CleanComponent (should pass) ---
[OK]    CleanComponent: render context collected — no leak

--- Test 2: LeakyComponent (should detect leak) ---
[LEAK]  LeakyComponent: render context is still alive!
        render context has 2 referrer(s):
          - cell: <cell at 0x10286c8b0: _RenderContext object at 0x1119c1f50>
          - cell: <cell at 0x10286c9d0: _RenderContext object at 0x1119c1f50>

============================================================
SUCCESS: Clean component passed, leaky component caught.
============================================================
```

The two `cell` referrers are closure cells from the `set_text` setter stored in `_leaked_references`. They close over the `_RenderContext`, preventing its collection.

## Diagnostic: what to do when a leak is found

When `rc_ref()` is not `None` after GC, use the following steps **in this order**:

### Step 1: Use `objgraph.find_backref_chain()` (most effective)

```python
import objgraph

obj = rc_ref()
chain = objgraph.find_backref_chain(obj, objgraph.is_proper_module, max_depth=20)
for i, item in enumerate(chain):
    type_name = type(item).__name__
    if hasattr(item, '__name__'):
        type_name += f" ({item.__name__})"
    print(f"  [{i:2d}] {type_name}")
```

This finds the shortest reference chain from your leaked object to a module-level root. The output directly shows you which module-level object is (transitively) holding the render context alive. This is the single most useful diagnostic — it replaces hours of manual `gc.get_referrers()` exploration.

### Step 2: Generate a visual graph for complex cases

```python
objgraph.show_backrefs([obj], filename="leak.pdf", max_depth=15)
```

Useful when there are multiple retention paths.

### Step 3: Targeted `gc.get_referrers()` for specific objects

Only after `objgraph` has pointed you to the right area of code, use `gc.get_referrers()` to inspect specific objects in the chain:

```python
referrers = gc.get_referrers(obj)
for r in referrers:
    if isinstance(r, dict):
        keys = [k for k, v in r.items() if v is obj]
        print(f"dict keys={keys}")
    else:
        print(f"{type(r).__name__}")
```

### Traps to avoid during investigation

- **Don't start with raw `gc.get_referrers()` BFS/DFS** — it produces overwhelming output (lists of lists of list_iterators of tuples of cells). You'll follow irrelevant chains and waste time.
- **Don't assume the first obvious suspect is the root cause** — there may be multiple independent retention paths. Fix one, re-test, and check if the leak persists. Example: `Context.render_context` holding a strong ref looked like the cause, but the actual root was `previous_reactive_watch` on a different object entirely.
- **Don't forget to check which Python file is actually imported** — if Solara is installed as a regular package (not editable), your edits to the source repo won't take effect. Check: `python -c "import solara.toestand; print(solara.toestand.__file__)"`.
- **Don't rely on `__del__` detection** — `hasattr(type(obj), '__del__')` gives false positives on built-in types (`cell`, `list`, `list_iterator`). On Python 3.4+ (PEP 442), `__del__` in cycles is not a collection barrier anyway.

### Common leak sources in Solara components

| Pattern | Why it leaks | Fix |
|---------|-------------|-----|
| Storing `set_state` in a global/module-level container | Setter closes over component state which references the render context | Use `weakref.ref` or avoid global storage |
| Callback/closure capturing `self` or component state | Closure keeps the captured objects alive | Use `weakref.ref` in the closure |
| Registering an event handler on a long-lived object | Handler closure pins component state | Unregister in cleanup / use weakref |
| Caching component output globally | Cache entry holds widget/state references | Use `weakref.WeakValueDictionary` or bound cache lifetime |
| Context manager not clearing saved state after `__exit__` | `__enter__` saves a reference (e.g. `self.previous_X = current_value`), `__exit__` restores it but doesn't clear the attribute | Set `self.previous_X = None` after restoring in `__exit__` |
| Bound method stored on a long-lived object | `obj.method` is a bound method that holds a strong ref to `obj` | Clear the attribute when the method's owner should be freed |
| `@slab.computed` reading during component render | `Computed`'s `AutoSubscribeContextManager` saves the component's watch callback as `previous_reactive_watch`, transitively pinning the render context | Clear `previous_reactive_watch` in `__exit__` (see [report](memory-leak-found-report-previous-reactive-watch.md)) |

## Incremental testing strategy

When testing a complex component, write tests **from simple to complex**:

1. **Baseline**: `sl.Text("hello")`, `sl.Column(...)`, `sl.Markdown(...)` — these validate the test harness itself
2. **Simple `@sl.component`**: components with no external state, just rendering
3. **Stateful**: components that read `sl.reactive` values
4. **Computed**: components that read `@slab.computed` values
5. **Full app**: the complete page with all dependencies mocked

When the first test fails, the component that introduced the failure is the differentiator. This narrows the search space from "somewhere in 2000 lines of UI code" to "something about `@slab.computed`."

## Running the demo

```bash
uv run python docs/memleak_demo.py
```

## Reference

- Full background: [docs/memory-leak-detection.md](memory-leak-detection.md)
- Demo script: [docs/memleak_demo.py](memleak_demo.py)
- Integration-level leak test: [tests/integration/memleak_test.py](../tests/integration/memleak_test.py)
- Leak report: `previous_reactive_watch`: [docs/memory-leak-found-report-previous-reactive-watch.md](memory-leak-found-report-previous-reactive-watch.md)
