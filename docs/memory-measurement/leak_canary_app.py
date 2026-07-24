"""Amplification canary for subscription-residue leaks.

The pattern under test: a component-scoped `@solara.lab.computed` that reads a
module-level reactive. The computed's auto-subscribe machinery registers a
listener on the module-level store under the kernel's scope id; the listener
closure captures everything the computed's function captures. If those
listener entries are not removed at kernel close, every session leaks the
captured payload — permanently, because the module-level store lives as long
as the process.

At natural scale the captured closures are a few KB and vanish inside the
allocator-retention noise of the cycle protocol. This app deliberately makes
the capture BIG (PAYLOAD_MB per page) so a per-session leak shows up as an
unmistakable constant increment in the idle-point series:

    python -m solara run docs/memory-measurement/leak_canary_app.py --production
    # or drive it with measure.py / measure_docker.py: marker text "CANARY-DONE"

Healthy behaviour: idle-point plateau after warmup (payload freed with the
kernel). Leak: ~PAYLOAD_MB x pages/cycle constant growth per cycle.

The object-level check, without measuring memory at all: after every cycle,
per-store listener counts must return to baseline (see
`dump_module_store_listeners()` below, and the "subscription residue" case
study in memory-usage-inspection.md).
"""

import solara
import solara.lab

# per-RENDER capture; a click on any page fires the shared reactive and re-renders
# every open page, so a 10-page cycle leaks ~(pages + total-fires) x PAYLOAD_MB.
# 1 MB keeps a 10-cycle run bounded while staying far above the noise floor.
PAYLOAD_MB = 1

# the process-lifetime store the leaked listeners accumulate on
counter = solara.reactive(0)


@solara.component
def Page():
    # per-render payload, captured by the computed's closure below
    payload = b"x" * (PAYLOAD_MB * 1024 * 1024)

    # component-scoped computed reading a module-level reactive: its
    # auto-subscribe listener (and this closure, and `payload`) is registered
    # on `counter` under this kernel's scope id
    @solara.lab.computed
    def derived():
        return counter.value, len(payload)

    # "Clicked: N" label: the measure.py harness clicks this button on every page
    solara.Button(label=f"Clicked: {counter.value}", on_click=lambda: counter.set(counter.value + 1))
    solara.Text(f"counter={derived.value[0]} payload={derived.value[1]} bytes")
    solara.Text("CANARY-DONE")


def dump_module_store_listeners(top: int = 10) -> list[tuple[str, int, int]]:
    """Per-store listener counts for module-level ValueBase instances.

    Enumerates sys.modules (NOT gc.get_objects: gc.freeze hides frozen stores
    from the gc APIs, and module dicts are visible either way). Returns
    (name, scopes, listeners) sorted by listener count; run it at the idle
    point of every cycle — the counts must return to the same baseline.
    """
    import sys

    from solara.toestand import ValueBase

    rows = []
    seen: set[int] = set()
    for mod_name, mod in list(sys.modules.items()):
        try:
            mod_vars = vars(mod)
        except TypeError:
            continue
        for attr, val in list(mod_vars.items()):
            candidates = [val]
            val_dict = getattr(val, "__dict__", None)
            if isinstance(val_dict, dict):
                candidates += [v for k, v in val_dict.items() if k in ("_storage", "_auto_subscriber")]
            for cand in candidates:
                if not isinstance(cand, ValueBase) or id(cand) in seen:
                    continue
                seen.add(id(cand))
                listeners = cand.__dict__.get("listeners") or {}
                listeners2 = cand.__dict__.get("listeners2") or {}
                scopes = set(listeners) | set(listeners2)
                count = sum(len(s) for s in listeners.values()) + sum(len(s) for s in listeners2.values())
                if scopes:
                    rows.append((f"{mod_name}.{attr}", len(scopes), count))
    rows.sort(key=lambda r: -r[2])
    return rows[:top]
