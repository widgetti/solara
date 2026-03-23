"""Tests for Starlette lifespan context manager."""

import asyncio
from unittest import mock


def test_lifespan_context_manager():
    """Test that the lifespan context manager calls on_startup and on_shutdown."""
    from solara.server.starlette import lifespan

    startup_called = []
    shutdown_called = []

    with mock.patch("solara.server.starlette.on_startup", lambda: startup_called.append(True)):
        with mock.patch("solara.server.starlette.on_shutdown", lambda: shutdown_called.append(True)):

            async def test_lifespan():
                async with lifespan(None):
                    assert startup_called == [True], "on_startup should be called before yield"
                    assert shutdown_called == [], "on_shutdown should not be called before yield"
                assert shutdown_called == [True], "on_shutdown should be called after yield"

            asyncio.run(test_lifespan())
