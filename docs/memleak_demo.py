"""Memory leak detection demo for Solara.

Demonstrates the weakref-based leak detection strategy described in
docs/memory-leak-detection.md. We create two components:

1. LeakyComponent — stores a callback in a global list every render,
   preventing the render context (and all widgets) from being collected.
2. CleanComponent — no global references, everything is collectable.

We render each one with solara.render_fixed(), take a weakref to the
render context, close it, delete locals, run gc.collect(), and check
whether the weakref resolves to None.

Note: We track the render context (_RenderContext), not the widget.
Widgets (ipyvue Html nodes) have internal bound methods that keep them
alive outside the kernel lifecycle — that's normal and handled by
Widget.close_all() in production.  The render context is the meaningful
object: if it leaks, the entire component tree and its state leak.
"""

import gc
import weakref

import solara

# ---------------------------------------------------------------------------
# The leak: a global list that accumulates strong references
# ---------------------------------------------------------------------------
_leaked_references: list = []


@solara.component
def LeakyComponent():
    text, set_text = solara.use_state("hello")
    # BUG: storing the setter globally prevents the entire render context
    # from being garbage collected, because set_text closes over the
    # component's internal state.
    _leaked_references.append(set_text)
    solara.Text(text)


@solara.component
def CleanComponent():
    text, set_text = solara.use_state("hello")
    # No global reference — everything stays local and can be collected.
    solara.Text(text)


# ---------------------------------------------------------------------------
# Detection helper — the core pattern from the doc
# ---------------------------------------------------------------------------
def _scoped_render(component_el):
    """Render inside a function so all locals die when we return.

    Returns only a weakref — the caller never holds a strong reference.
    """
    widget, rc = solara.render_fixed(component_el, handle_error=False)
    rc_ref = weakref.ref(rc)

    # Normal lifecycle cleanup
    rc.close()

    # Drop our strong references
    del widget, rc

    return rc_ref


def check_leak(name: str, component_el) -> bool:
    """Returns True if a leak is detected (render context still alive)."""
    rc_ref = _scoped_render(component_el)

    # Aggressive GC — multiple passes across all generations
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Memory Leak Detection Demo")
    print("=" * 60)
    print()

    # 1. Baseline — clean component should NOT leak
    print("--- Test 1: CleanComponent (should pass) ---")
    leaked_clean = check_leak("CleanComponent", CleanComponent())
    print()

    # 2. Leaky component — SHOULD leak
    print("--- Test 2: LeakyComponent (should detect leak) ---")
    leaked_leaky = check_leak("LeakyComponent", LeakyComponent())
    print()

    # Summary
    print("=" * 60)
    if not leaked_clean and leaked_leaky:
        print("SUCCESS: Clean component passed, leaky component caught.")
    elif leaked_clean:
        print("UNEXPECTED: Clean component leaked — something else is wrong.")
    elif not leaked_leaky:
        print("UNEXPECTED: Leaky component was NOT caught — detection failed.")
    print("=" * 60)

    # Cleanup the global list so it doesn't affect anything else
    _leaked_references.clear()


if __name__ == "__main__":
    main()
