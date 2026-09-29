"""SOLARA_STATE_REDIS_CLIENT_FACTORY: a deployment supplies the redis state backend's client."""

import sys
import types

import fakeredis
import pytest

import solara.server.settings
import solara.state
from solara.state.redis import RedisStateBackend

SESSION = b"session-hmac"
SCHEMA_TAG = "v1"


@pytest.fixture
def factory_module(monkeypatch):
    module = types.ModuleType("my_state_redis")
    calls = []

    def make_client(settings):
        calls.append(settings)
        return fakeredis.FakeRedis()

    module.make_client = make_client  # type: ignore[attr-defined]
    module.not_callable = 42  # type: ignore[attr-defined]
    module.calls = calls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "my_state_redis", module)
    return module


def test_client_factory_setting(monkeypatch, factory_module):
    monkeypatch.setattr(solara.server.settings.state, "url", "")  # the factory owns the connection details
    monkeypatch.setattr(solara.server.settings.state, "redis_client_factory", "my_state_redis.make_client")
    backend = RedisStateBackend()
    assert factory_module.calls == [solara.server.settings.state]
    assert isinstance(backend.client, fakeredis.FakeRedis)
    assert backend.takeover("k", SESSION, SCHEMA_TAG).reason == "miss"


def test_no_client_factory_builds_the_built_in_client(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "url", "redis://127.0.0.1:1/0")
    monkeypatch.setattr(solara.server.settings.state, "redis_client_factory", "")
    client = RedisStateBackend.__new__(RedisStateBackend)._make_client()
    assert client.connection_pool.connection_kwargs["port"] == 1


@pytest.mark.parametrize("path", ["my_state_redis.missing", "no_such_module_xyz.make_client", "my_state_redis.not_callable"])
def test_validate_rejects_a_bad_client_factory(monkeypatch, factory_module, path):
    monkeypatch.setattr(solara.server.settings.state, "backend", "redis")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    monkeypatch.setattr(solara.server.settings.state, "redis_client_factory", path)
    with pytest.raises(ValueError, match="SOLARA_STATE_REDIS_CLIENT_FACTORY"):
        solara.state.validate_state_settings()


def test_validate_accepts_a_client_factory(monkeypatch, factory_module):
    monkeypatch.setattr(solara.server.settings.state, "backend", "redis")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    monkeypatch.setattr(solara.server.settings.state, "redis_client_factory", "my_state_redis.make_client")
    solara.state.validate_state_settings()


def test_validate_ignores_the_client_factory_for_other_backends(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    monkeypatch.setattr(solara.server.settings.state, "redis_client_factory", "no_such_module_xyz.make_client")
    solara.state.validate_state_settings()
