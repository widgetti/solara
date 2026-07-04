"""Single-process soft-remount acceptance test for opt-in reactive state persistence.

This is the user-visible acceptance test for commit 4 of the state-persistence feature
(design §6.4/§6.5/§9). It exercises the REAL restore path in a single process: the memory
backend keeps the (codec-encoded, HMAC-signed) envelope bytes keyed by kernel id, while the
dev/test kernel eviction removes the in-memory kernel context. ``simulateFailover()``
combines both halves - evict server-side (over the kernel websocket, so it reaches the owning
instance through any load balancer), then drop the socket - so the reconnect behaves exactly
like landing on a fresh instance behind a load balancer.

What we assert after failover:
  - the persisted reactive is restored (``Value 2`` survives),
  - a non-persisted ``use_state`` counter resets to its default (the honest recovery model,
    §6.5: persist inputs, recompute/reset the rest),
  - a ``use_memo`` derived from the persisted value recomputes (``Doubled 4``),
  - NO refresh dialog ("Please refresh the page") appears - the app soft-remounts,
  - ``solara.debug.lastRestore.status === "success"`` and ``remountCount === 1``.

Eviction fails closed; the second test pins the fail-closed gate of the HTTP evict route
(404 when ``SOLARA_STATE_TEST_EVICTION`` is off) without a browser (the ws comm gate is
pinned in tests/unit/state_server_test.py).
"""

import uuid
from pathlib import Path

import playwright.sync_api
import pytest
import requests

import solara
import solara.server.settings
import solara.state
import solara.server.kernel_context
from solara.state import persist, stats

HERE = Path(__file__).parent

# --- the test app (module-level, like reconnect_test.py) ----------------------------------
# One persisted reactive with an explicit, cross-process-stable key. Explicit keys are the
# norm for anything meant to survive a failover (design §4.1).
count = solara.reactive(0, persist=True, key="test.reconnect.count")


@solara.component
def Page():
    # a NON-persisted use_state counter: this MUST reset to 0 after a soft-remount - the
    # honest recovery model (design §6.5). Rendered so the test can assert the reset.
    ephemeral, set_ephemeral = solara.use_state(0)
    # a derived value from the persisted input: it must RECOMPUTE on the fresh render after
    # remount (persist inputs, recompute outputs - §6.5), never be persisted itself.
    doubled = solara.use_memo(lambda: count.value * 2, [count.value])

    solara.Text(f"Value {count.value}")
    solara.Text(f"Ephemeral {ephemeral}")
    solara.Text(f"Doubled {doubled}")

    def increment_count():
        count.value += 1

    solara.Button("IncrementCount", on_click=increment_count)
    solara.Button("IncrementEphemeral", on_click=lambda: set_ephemeral(ephemeral + 1))


# --- fixtures -----------------------------------------------------------------------------


@pytest.fixture
def state_settings(monkeypatch):
    """Configure the in-process server for memory-backed persistence + the eviction route.

    Settings reach the server via ``solara.server.settings.state`` (the backend is read at
    ``get_backend()`` time via a cached singleton), so we mutate the shared settings object and
    reset the singletons. We deliberately do NOT reset the persist registry here (unlike the
    unit-test autouse fixture): the persisted reactive above is registered at MODULE import, so
    clearing the registry would unregister it and disable persistence for the test app.
    """
    monkeypatch.setattr(solara.server.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "integration-test-secret-key")
    monkeypatch.setattr(solara.server.settings.state, "schema_tag", "integration-schema-1")
    # a short debounce plus the bounded final flush on evict makes the flush deterministic
    monkeypatch.setattr(solara.server.settings.state, "flush_debounce", "50ms")
    monkeypatch.setattr(solara.server.settings.state, "test_eviction", True)
    solara.state.reset_backend()
    solara.state.reset_breaker()
    stats()._reset()
    yield
    # close any context the test left open (stops flush worker threads), then reset singletons.
    # monkeypatch restores the settings values; the persist registry is left intact.
    for context in list(solara.server.kernel_context.contexts.values()):
        try:
            context.close(reason="evicted")
        except Exception:  # noqa
            pass
    solara.state.reset_backend()
    solara.state.reset_breaker()
    stats()._reset()
    persist._attached_managers.clear()


# --- the marquee acceptance test ----------------------------------------------------------


def test_state_persistence_soft_remount(
    browser: playwright.sync_api.Browser,
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    extra_include_path,
    request,
    state_settings,
):
    # the evict goes over the solara.control comm (server-agnostic), so this runs on flask too
    try:
        with extra_include_path(HERE), solara_app("reconnect_state_test:Page"):
            page_session.goto(solara_server.base_url)
            page_session.locator("text=Value 0").wait_for()
            page_session.locator("text=Ephemeral 0").wait_for()
            page_session.locator("text=Doubled 0").wait_for()

            # bump the NON-persisted counter so we can prove it resets after failover
            page_session.locator("text=IncrementEphemeral").click()
            page_session.locator("text=Ephemeral 1").wait_for()

            # bump the PERSISTED counter twice; "Doubled" must track it (derived)
            page_session.locator("text=IncrementCount").click()
            page_session.locator("text=Value 1").wait_for()
            page_session.locator("text=IncrementCount").click()
            page_session.locator("text=Value 2").wait_for()
            page_session.locator("text=Doubled 4").wait_for()

            assert len(solara.server.kernel_context.contexts) == 1

            # REAL failover in one process: evict the kernel context server-side (so the in-memory
            # kernel is gone, exactly as if the LB moved us to a fresh instance), then drop the
            # socket. Only the memory-backend hash survives. simulateFailover() awaits the evict
            # reply on the solara.control comm before dropping, and page.evaluate awaits the
            # returned promise.
            page_session.evaluate("solara.debug.simulateFailover()")

            # the client soft-remounts on reconnect (no dialog); remountCount increments AFTER a
            # successful mount swap, so this is the deterministic sync point (no sleeps).
            page_session.wait_for_function("() => window.solara && solara.debug && solara.debug.remountCount === 1", timeout=30000)

            # persisted state restored (a fresh, unrestored render would show "Value 0")
            page_session.locator("text=Value 2").wait_for()
            # derived value recomputed from the restored input
            page_session.locator("text=Doubled 4").wait_for()
            # non-persisted use_state reset to its default (honest recovery model)
            page_session.locator("text=Ephemeral 0").wait_for()

            # NO refresh dialog on the soft-remount path
            assert page_session.locator("text=Please refresh the page").count() == 0

            # observability surface the tests/devtools rely on (§6.4)
            assert page_session.evaluate("solara.debug.lastRestore && solara.debug.lastRestore.status") == "success"
            assert page_session.evaluate("solara.debug.reconnectCount") >= 1

            # no extra context leaked; the reconnect reused the same kernel id (fresh context)
            assert len(solara.server.kernel_context.contexts) == 1
    finally:
        # reset the shared session page for the next test
        page_session.goto("about:blank")


# --- stale-comm purge on soft-remount (regression for the cross-node comm collision) -------


def test_soft_remount_purges_stale_comms(
    browser: playwright.sync_api.Browser,
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    extra_include_path,
    request,
    state_settings,
):
    """A soft-remount must not leak the disposed generation's comms on the kernel connection.

    Mechanism (confirmed against @jupyter-widgets/base): the silent local teardown closes each
    widget model with ``close(true)`` ("comm already closed remotely"), which deletes the model's
    reference to its comm but does NOT unregister the CommHandler from the connection's ``_comms``
    map. Those orphans are inert on the same node, but when a later reconnect lands on a DIFFERENT
    node that still serves one of those ids, the resync (``_loadFromKernel`` -> ``createComm(id)``)
    throws "Comm is already created" mid-map and leaves half the widget tree detached (its inputs
    never sync to python again - e.g. a login button that can never enable). Observed on a
    round-robin staging deploy.

    We can't stand up two nodes in-process, but we can pin the fix's precondition deterministically:
    after a real single-process soft-remount, NONE of the comm ids that were registered before the
    remount may still be registered on the connection. Without the purge they linger (RED); with it
    they are disposed (GREEN). We also assert the collision error never surfaces and the app stays
    interactive.
    """
    page_errors: list = []
    page_session.on("pageerror", lambda exc: page_errors.append(str(exc)))
    try:
        with extra_include_path(HERE), solara_app("reconnect_state_test:Page"):
            page_session.goto(solara_server.base_url)
            page_session.locator("text=Value 0").wait_for()

            # comm ids registered on the connection for THIS (pre-remount) generation
            comm_ids_before = set(page_session.evaluate("Array.from(solara.debug.kernel()._comms.keys())"))
            assert comm_ids_before, "expected the kernel connection to have registered comms before failover"

            # real single-process failover -> soft-remount (same path as the marquee test)
            page_session.evaluate("solara.debug.simulateFailover()")
            page_session.wait_for_function("() => window.solara && solara.debug && solara.debug.remountCount === 1", timeout=30000)
            page_session.locator("text=Value 0").wait_for()

            # the disposed generation's comms must be gone from the connection registry
            comm_ids_after = set(page_session.evaluate("Array.from(solara.debug.kernel()._comms.keys())"))
            leaked = comm_ids_before & comm_ids_after
            assert not leaked, f"stale comms from before the remount still registered on the kernel connection: {leaked}"

            # the collision itself must never have surfaced
            assert not any("Comm is already created" in e for e in page_errors), page_errors

            # app still interactive after the remount: the button syncs to python
            page_session.locator("text=IncrementCount").click()
            page_session.locator("text=Value 1").wait_for()
            assert not any("Comm is already created" in e for e in page_errors), page_errors
    finally:
        page_session.goto("about:blank")


# --- fail-closed gate (cheap negative, no browser) ----------------------------------------


def test_eviction_route_disabled_returns_404(solara_server, request, monkeypatch):
    """The kernel-eviction route must fail closed: 404 when SOLARA_STATE_TEST_EVICTION is off."""
    if request.node.callspec.params.get("solara_server") != "starlette":
        pytest.skip("The kernel-eviction route only exists on the starlette server.")
    monkeypatch.setattr(solara.server.settings.state, "test_eviction", False)
    kernel_id = str(uuid.uuid4())
    url = f"{solara_server.base_url}/_solara/api/evict/{kernel_id}"
    response = requests.post(url, timeout=10)
    assert response.status_code == 404
