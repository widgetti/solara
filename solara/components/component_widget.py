"""Shared widget construction helpers for frontend-backed components."""

from __future__ import annotations

import inspect
from typing import Any, Callable

import ipywidgets as widgets
import traitlets

default_to_json = widgets.widget_serialization["to_json"]
default_from_json = widgets.widget_serialization["from_json"]


def widget_from_signature(
    classname: str,
    base_class: type[widgets.Widget],
    func: Callable[..., None],
    event_prefix: str,
    tags: dict[str, Any],
    to_json: dict[str, Callable[[Any, widgets.Widget], Any]],
    from_json: dict[str, Callable[[Any, widgets.Widget], Any]],
) -> type[widgets.Widget]:
    """Build a widget class whose synchronized traits follow ``func``'s signature.

    ``event_prefix`` identifies the event methods expected by the frontend
    renderer (for example, ``vue_`` for ipyvue).
    """
    classprops: dict[str, Any] = {}
    parameters = inspect.signature(func).parameters
    for name, param in parameters.items():
        if name.startswith("event_"):
            event_name = name[6:]
            event_name_full = name  # Keep the event_foo alias for compatibility.

            def event_handler(self, data, buffers=None, event_name=event_name, event_name_full=event_name_full, param=param):
                callback = self._event_callbacks.get(event_name, param.default)
                if not callback:
                    callback = self._event_callbacks.get(event_name_full, None)
                if callback:
                    if buffers:
                        callback(data, buffers)
                    else:
                        callback(data)

            classprops[f"{event_prefix}{event_name}"] = event_handler
            classprops[f"{event_prefix}{event_name_full}"] = event_handler
        elif name.startswith("on_") and name[3:] in parameters:
            # Reacton owns the callback for a corresponding synced trait.
            continue
        else:
            trait = traitlets.Any() if param.default == inspect.Parameter.empty else traitlets.Any(default_value=param.default)
            tag = {"sync": True, "to_json": to_json.get(name, default_to_json), "from_json": from_json.get(name, default_from_json)}
            tag.update(**tags.get(name, {}))
            classprops[name] = trait.tag(**tag)

    # Maps event_foo to a callable supplied by the component caller.
    classprops["_event_callbacks"] = traitlets.Dict(default_value={})
    return type(classname, (base_class,), classprops)
