"""Lazy accessor for the state-persistence settings.

The ``State`` settings live in ``solara.server.settings`` — persistence is a server-only
feature and its knobs are coupled to server siblings (``Kernel.cull_timeout``,
``Session.secret_key``, ``main.mode``). The import is lazy so that ``import solara``
(which eagerly pulls ``solara.state.persist`` for ``PersistConfig``) never drags server
modules at import time — the same pattern ``solara/routing.py`` uses.
"""


def state_settings():
    import solara.server.settings

    return solara.server.settings.state
