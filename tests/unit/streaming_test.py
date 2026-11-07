import asyncio
import subprocess
import sys
import threading
from typing import List
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import anyio
import httpx
import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import ASGIApp, Message
from starlette.websockets import WebSocket

import solara
from solara.server import kernel_context, server, settings, starlette, streaming


def test_register_stream_import():
    subprocess.run([sys.executable, "-c", "from solara.server.streaming import register_stream"], check=True, timeout=15)


@pytest.fixture
def make_kernel():
    contexts = []

    def create(session_id="owner", root_path="", user=None):
        context = kernel_context.initialize_virtual_kernel(session_id, uuid4().hex, Mock())
        assert context is not None
        contexts.append(context)
        streaming._configure(context, root_path, user)
        return context

    yield create

    for context in contexts:
        if not context.closed_event.is_set():
            context.close()


def register(context, factory):
    binding = streaming._connection_owner.set(context._stream_owner)
    try:
        with context:
            return streaming.register_stream(factory)
    finally:
        streaming._connection_owner.reset(binding)


@pytest.mark.parametrize("fastapi", [False, True])
async def test_owner_can_claim_once(make_kernel, fastapi):
    app: ASGIApp = starlette.app
    if fastapi:
        pytest.importorskip("fastapi")
        from solara.server.fastapi import app as fastapi_app

        app = fastapi_app
    context = make_kernel(root_path="/mounted")
    calls = 0

    async def produce():
        nonlocal calls
        calls += 1
        yield b"data"

    url = register(context, produce)
    assert url.startswith("/mounted/_solara/api/streams/")
    assert calls == 0
    mounted = Starlette(routes=[Mount("/mounted", app=app)])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mounted), base_url="http://test") as client:
        unknown = await client.get(url + "-unknown")
        missing = await client.get(url)
        foreign = await client.get(url, headers={"Cookie": f"{server.COOKIE_KEY_SESSION_ID}=other"})
        owner = {"Cookie": f"{server.COOKIE_KEY_SESSION_ID_LAX}=owner"}
        head = await client.head(url, headers=owner)
        assert unknown.status_code == missing.status_code == foreign.status_code == head.status_code == 404
        assert unknown.content == missing.content == foreign.content
        assert unknown.headers == missing.headers == foreign.headers
        assert calls == 0
        results = await asyncio.gather(client.get(url, headers=owner), client.get(url, headers=owner))
        assert sorted(response.status_code for response in results) == [200, 404]
        assert next(response.content for response in results if response.status_code == 200) == b"data"
        assert calls == 1
        assert (await client.get(url, headers=owner)).status_code == 404


@pytest.mark.parametrize("configured", [None, "/public/mounted"])
async def test_kernel_stream_uses_public_root(monkeypatch, configured):
    monkeypatch.setattr(settings.main, "root_path", configured)
    monkeypatch.setattr(settings.kernel, "threaded", False)
    app_loop = AsyncMock()
    monkeypatch.setattr(server, "app_loop", app_loop)
    ws = WebSocket(
        {
            "type": "websocket",
            "root_path": "/mounted",
            "path_params": {"kernel_id": "kernel"},
            "query_string": b"session_id=page",
            "headers": [(b"cookie", f"{server.COOKIE_KEY_SESSION_ID}=owner".encode())],
        },
        AsyncMock(return_value={"type": "websocket.connect"}),
        AsyncMock(),
    )
    await starlette.kernel_connection(ws)
    assert app_loop.call_args.kwargs["stream_root_path"] == (configured or "/mounted")


def test_first_chunk_arrives_before_completion(make_kernel):
    context = make_kernel()
    allow_finish = threading.Event()
    finished = threading.Event()

    async def produce():
        yield b"first"
        while not allow_finish.is_set():
            await asyncio.sleep(0.01)
        yield b"last"
        finished.set()

    url = register(context, produce)
    live_server = starlette.ServerStarlette(port=0, lifespan="off")
    live_server.serve_threaded()
    try:
        live_server.wait_until_serving()
        headers = {"Cookie": f"{server.COOKIE_KEY_SESSION_ID}=owner", "Accept-Encoding": "gzip"}
        with httpx.stream("GET", live_server.base_url + url, headers=headers, timeout=5, trust_env=False) as response:
            assert response.status_code == 200
            assert response.headers["Content-Encoding"] == "identity"
            assert response.headers["Cache-Control"] == "no-store, no-transform"
            assert response.headers["X-Accel-Buffering"] == "no"
            assert "Content-Length" not in response.headers
            body = response.iter_raw()
            assert next(body) == b"first"
            assert not finished.is_set()
            allow_finish.set()
            assert b"".join(body) == b"last"
            assert finished.wait(1)
    finally:
        allow_finish.set()
        live_server.stop_serving()


def request_scope(url):
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": url,
        "headers": [(b"cookie", f"{server.COOKIE_KEY_SESSION_ID}=owner".encode())],
        "query_string": b"",
    }


def start_request(url, messages, *, send=None):
    incoming: asyncio.Queue[Message] = asyncio.Queue()
    incoming.put_nowait({"type": "http.request", "body": b"", "more_body": False})

    async def capture(message):
        messages.append(message)

    return incoming, asyncio.create_task(starlette.app(request_scope(url), incoming.get, send or capture))


@pytest.mark.parametrize("action", ["disconnect", "close", "restart"])
@pytest.mark.parametrize("first_chunk", [False, True])
async def test_stream_cancellation(make_kernel, action, first_chunk):
    context = make_kernel()
    waiting = asyncio.Event()
    cleaned = asyncio.Event()
    messages: List[Message] = []

    async def read_kernel_id():
        return solara.get_kernel_id(ipython_fallback=False)

    async def produce():
        try:
            if first_chunk:
                yield b"first"
            waiting.set()
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            assert await asyncio.gather(read_kernel_id()) == [context.id]
            cleaned.set()

    url = register(context, produce)
    pending = register(context, produce)
    incoming, response = start_request(url, messages)
    await asyncio.wait_for(waiting.wait(), 2)
    assert bool(messages) == first_chunk
    if action == "disconnect":
        incoming.put_nowait({"type": "http.disconnect"})
    elif action == "close":
        await asyncio.get_running_loop().run_in_executor(None, context.close)
    else:
        await asyncio.get_running_loop().run_in_executor(None, context.restart)
    if first_chunk and action != "disconnect":
        with pytest.raises(RuntimeError, match="stream interrupted"):
            await asyncio.wait_for(response, 2)
    else:
        await asyncio.wait_for(response, 2)
    assert cleaned.is_set()
    assert url.rsplit("/", 1)[-1] not in streaming._streams
    if action != "disconnect":
        assert pending.rsplit("/", 1)[-1] not in streaming._streams
        messages.clear()
        _, denied = start_request(pending, messages)
        await asyncio.wait_for(denied, 2)
        assert messages[0]["status"] == 404


async def test_blocked_send_applies_backpressure_and_closes_generator(make_kernel):
    context = make_kernel()
    sending = asyncio.Event()
    cleaned = asyncio.Event()
    pulled_again = False

    async def produce():
        nonlocal pulled_again
        try:
            yield b"first"
            pulled_again = True
            yield b"last"
        finally:
            await asyncio.sleep(0)
            assert solara.get_kernel_id() == context.id
            cleaned.set()

    async def slow_send(message):
        if message["type"] == "http.response.body":
            sending.set()
            await asyncio.Event().wait()

    incoming, response = start_request(register(context, produce), [], send=slow_send)
    await asyncio.wait_for(sending.wait(), 2)
    assert not pulled_again
    incoming.put_nowait({"type": "http.disconnect"})
    await asyncio.wait_for(response, 2)
    assert cleaned.is_set()
    assert not pulled_again


async def test_outer_asgi_cancellation_allows_generator_cleanup(make_kernel):
    waiting = asyncio.Event()
    cleaned = asyncio.Event()

    async def produce():
        try:
            waiting.set()
            await asyncio.Event().wait()
            yield b""
        finally:
            await asyncio.sleep(0.01)
            cleaned.set()

    async def receive():
        await asyncio.Event().wait()

    async def send(message):
        pytest.fail("Cancelled request sent a response")

    url = register(make_kernel(), produce)
    with anyio.fail_after(2):
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(starlette.app, request_scope(url), receive, send)
            await waiting.wait()
            tasks.cancel_scope.cancel()
    assert cleaned.is_set()
    assert url.rsplit("/", 1)[-1] not in streaming._streams


async def test_restart_between_claim_and_factory(make_kernel, monkeypatch):
    context = make_kernel()
    original_claim = streaming._claim
    called = False

    def claim(*args):
        stream = original_claim(*args)
        if stream is not None:
            context.restart()
        return stream

    async def produce():
        nonlocal called
        called = True
        yield b"data"

    monkeypatch.setattr(streaming, "_claim", claim)
    messages: List[Message] = []
    _, response = start_request(register(context, produce), messages)
    await asyncio.wait_for(response, 2)
    assert messages[0]["status"] == 404
    assert not called


async def test_expiry_releases_capacity(make_kernel, monkeypatch):
    monkeypatch.setattr(streaming, "_LIMIT", 1)
    monkeypatch.setattr(streaming, "_TTL", 0.2)
    context = make_kernel()

    async def produce():
        pytest.fail("Expired factory was called")
        yield b""

    url = register(context, produce)
    with pytest.raises(RuntimeError, match="limit"):
        register(context, produce)
    token = url.rsplit("/", 1)[-1]

    async def wait_for_expiry():
        while token in streaming._streams:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(wait_for_expiry(), 2)
    assert register(context, produce) != url
    messages: List[Message] = []
    _, response = start_request(url, messages)
    await asyncio.wait_for(response, 2)
    assert messages[0]["status"] == 404


@pytest.mark.parametrize("threaded", [False, True])
async def test_stream_context_isolation(make_kernel, monkeypatch, threaded):
    monkeypatch.setattr(settings.kernel, "threaded", threaded)
    first, second = make_kernel(), make_kernel()
    value = solara.reactive("")
    both_started = asyncio.Event()
    seen = set()

    async def read_context():
        await asyncio.sleep(0)
        return solara.get_kernel_id(ipython_fallback=False), value.value

    async def produce():
        kernel_id = solara.get_kernel_id()
        seen.add(kernel_id)
        if len(seen) == 2:
            both_started.set()
        await both_started.wait()
        assert solara.get_kernel_id() == kernel_id
        assert value.value == kernel_id
        assert await asyncio.gather(read_context()) == [(kernel_id, kernel_id)]
        yield kernel_id.encode()

    for context in (first, second):
        with context:
            value.set(context.id)

    async def read(context):
        messages: List[Message] = []
        _, response = start_request(register(context, produce), messages)
        await asyncio.wait_for(response, 2)
        assert messages[1]["body"] == context.id.encode()

    baseline = kernel_context.current_context.copy()
    await asyncio.gather(read(first), read(second))
    assert kernel_context.current_context == baseline


async def test_stream_child_scopes_are_local_and_expire(make_kernel):
    owner, other = make_kernel(), make_kernel()
    entered = asyncio.Event()
    sibling_read = asyncio.Event()
    released = asyncio.Event()

    async def override():
        async with other:
            entered.set()
            await sibling_read.wait()
            assert solara.get_kernel_id(ipython_fallback=False) == other.id
        with kernel_context.without_context():
            assert not kernel_context.has_current_context()
        assert solara.get_kernel_id(ipython_fallback=False) == owner.id

    async def sibling():
        await entered.wait()
        assert solara.get_kernel_id(ipython_fallback=False) == owner.id
        sibling_read.set()

    async def late_child():
        await released.wait()
        return kernel_context.has_current_context()

    with kernel_context._use_stream_context(owner):
        await asyncio.wait_for(asyncio.gather(override(), sibling()), 2)
        child = asyncio.create_task(late_child())
    released.set()
    assert not await asyncio.wait_for(child, 2)


@pytest.mark.parametrize("first_chunk", [False, True])
async def test_upstream_error(make_kernel, first_chunk):
    async def produce():
        if first_chunk:
            yield b"data"
        raise ConnectionResetError("upstream")

    messages: List[Message] = []
    _, response = start_request(register(make_kernel(), produce), messages)
    if first_chunk:
        with pytest.raises(RuntimeError, match="stream interrupted"):
            await asyncio.wait_for(response, 2)
        assert messages[-1]["more_body"]
    else:
        await asyncio.wait_for(response, 2)
        assert messages[0]["status"] == 500


def test_oauth_subject_binding(make_kernel):
    user = {"userinfo": {"sub": "reader"}}
    context = make_kernel(user=user)

    async def produce():
        yield b"data"

    url = register(context, produce)
    token = url.rsplit("/", 1)[-1]
    assert streaming._claim(token, "owner", None, lambda: None) is None
    assert streaming._claim(token, "owner", {"userinfo": {"sub": "other"}}, lambda: None) is None
    assert streaming._claim(token, "owner", user, lambda: None) is not None
    with pytest.raises(RuntimeError, match="stable authenticated identity"):
        register(make_kernel(user={"userinfo": {}}), produce)


def test_reconnected_principal_cannot_inherit_an_old_connection_registration(make_kernel):
    context = make_kernel(user={"userinfo": {"sub": "original"}})

    async def produce():
        yield b"data"

    original = register(context, produce).rsplit("/", 1)[-1]
    binding = streaming._connection_owner.set(context._stream_owner)
    try:
        replacement = {"userinfo": {"sub": "replacement"}}
        streaming._configure(context, "", replacement)
        assert streaming._claim(original, "owner", replacement, lambda: None) is None
        with context, pytest.raises(RuntimeError, match="stable authenticated identity"):
            streaming.register_stream(produce)
    finally:
        streaming._connection_owner.reset(binding)
