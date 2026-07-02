"""Cross-instance failover demo for opt-in reactive state persistence.

Run this behind Caddy's round-robin load balancer with TWO solara backends sharing ONE Redis
(see README.md). Build up some state, then trigger a reconnect:

  * click "Disconnect websocket" (closes the server-side socket, the pattern from
    tests/integration/reconnect_test.py) - with round_robin the reconnect lands on the OTHER
    backend, i.e. a REAL cross-instance failover, or
  * open the browser devtools console and run  solara.debug.simulateFailover()  - which also
    works in a single `solara run` process with the memory backend (no infra needed).

What you should see after the reconnect:
  * the persisted inputs (filter + threshold) are RESTORED - no refresh dialog, no reload,
  * the "expensive" task RECOMPUTES from those restored inputs (persist inputs, recompute
    outputs),
  * the non-persisted "scratch note" RESETS to empty (the honest recovery model),
  * the fencing epoch (solara.state_generation()) INCREASES by one.

Docs: https://solara.dev/documentation/advanced/understanding/state-persistence
"""

import time

import solara
import solara.lab
import solara.server.kernel_context

# --- persisted inputs -----------------------------------------------------------------------
# persist=True opts these in; key= is their stable, cross-process persistence key. These two
# reactives are the ONLY state that survives a failover - everything else is re-derived.
text_filter = solara.reactive("a", persist=True, key="demo.failover.text_filter")
threshold = solara.reactive(30, persist=True, key="demo.failover.threshold")

FRUITS = [
    "apple",
    "apricot",
    "avocado",
    "banana",
    "blueberry",
    "cherry",
    "date",
    "elderberry",
    "fig",
    "grape",
    "kiwi",
    "lemon",
    "mango",
    "nectarine",
    "orange",
    "papaya",
    "raspberry",
    "strawberry",
]


@solara.component
def Page():
    # a NON-persisted field. It is held only in this kernel's memory, so it RESETS on failover -
    # this is the honest recovery model: persist what matters, let the rest re-derive/reset.
    note, set_note = solara.use_state("")

    # an "expensive computation" DERIVED from the persisted inputs. It is deliberately NOT
    # persisted: on the new instance it simply re-runs from the restored inputs, exactly as it
    # did on the original cold start. The 1.5s sleep stands in for a real database/API call.
    def expensive_query():
        time.sleep(1.5)
        needle = text_filter.value.lower()
        matches = [f for f in FRUITS if needle in f and len(f) <= threshold.value]
        return matches

    result = solara.lab.use_task(expensive_query, dependencies=[text_filter.value, threshold.value])

    generation = solara.state_generation()

    with solara.Column(gap="16px", style={"max-width": "720px", "margin": "0 auto", "padding": "24px"}):
        solara.Markdown("# State-persistence failover demo")
        solara.Markdown("Change the inputs below, then trigger a reconnect and watch your state come back on a **different** backend.")

        with solara.Card("Persisted inputs (these survive failover)"):
            solara.InputText("Filter fruits by name", value=text_filter)
            solara.SliderInt("Maximum name length", value=threshold, min=1, max=12)

        with solara.Card("Derived output (recomputed, never persisted)"):
            if result.pending:
                solara.Text("Computing... (pretend this hits a database)")
                solara.ProgressLinear(True)
            elif result.finished:
                matches = result.value or []
                solara.Text(f"Matches ({len(matches)}): {', '.join(matches) if matches else 'none'}")
            elif result.error:
                solara.Error(f"Computation failed: {result.exception}")

        with solara.Card("Scratch note (NOT persisted - this one resets)"):
            solara.InputText("Type something ephemeral here", value=note, on_value=set_note)
            solara.Text(f"Current note: {note!r}")

        with solara.Card("Failover controls"):
            solara.Markdown(
                f"**Fencing epoch** (`solara.state_generation()`): `{generation}` "
                "— increases by one on every failover.\n\n"
                "Trigger a failover in one of two ways:\n\n"
                "1. Click **Disconnect websocket** below. Behind Caddy `round_robin` the reconnect "
                "lands on the *other* backend — a real cross-instance failover.\n"
                "2. Open the browser devtools console and run "
                "`solara.debug.simulateFailover()` (works in a single `solara run` process with "
                "the memory backend, too)."
            )

            def disconnect():
                # close the server-side websocket(s) for this kernel; the client reconnects and,
                # behind the load balancer, is routed to the other backend (§9). Mirrors
                # tests/integration/reconnect_test.py:25-27.
                context = solara.server.kernel_context.get_current_context()
                for ws in list(context.kernel.session.websockets):
                    ws.close()

            solara.Button("Disconnect websocket", color="warning", on_click=disconnect)
