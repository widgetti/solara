"""Python API for native, single-file HTML components."""

from __future__ import annotations

import inspect
import os
from typing import Any, Callable

import ipywidgets as widgets
import traitlets
import typing_extensions

import solara
from solara.components.component_widget import widget_from_signature
from solara.components.html_component_assets import register_component_asset
from solara.components.html_component_file import parse_component_html

P = typing_extensions.ParamSpec("P")


def _register_asset(content: str | None, extension: str) -> str:
    if content is None:
        return ""
    return register_component_asset(content, extension)


class HTMLComponentWidget(widgets.DOMWidget):
    """Widget model shared by Python HTML components and their frontend view."""

    _model_name = traitlets.Unicode("HTMLComponentModel").tag(sync=True)
    _view_name = traitlets.Unicode("HTMLComponentView").tag(sync=True)
    _model_module = traitlets.Unicode("solara-html").tag(sync=True)
    _view_module = traitlets.Unicode("solara-html").tag(sync=True)
    _model_module_version = traitlets.Unicode("0.1.0").tag(sync=True)
    _view_module_version = traitlets.Unicode("0.1.0").tag(sync=True)

    template = traitlets.Unicode().tag(sync=True)
    css_asset = traitlets.Unicode("").tag(sync=True)
    script_asset = traitlets.Unicode("").tag(sync=True)
    prop_names = traitlets.List(traitlets.Unicode(), default_value=[]).tag(sync=True)
    event_names = traitlets.List(traitlets.Unicode(), default_value=[]).tag(sync=True)
    children = traitlets.Any(default_value=None).tag(
        sync=True,
        to_json=widgets.widget_serialization["to_json"],
        from_json=widgets.widget_serialization["from_json"],
    )

    _html_event_names: tuple = ()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on_msg(self._handle_html_event)

    def _handle_html_event(self, _widget, content, buffers):
        if not isinstance(content, dict) or content.get("type") != "event":
            return
        event_name = content.get("name")
        if not isinstance(event_name, str) or event_name not in self._html_event_names:
            return
        handler = getattr(self, f"html_{event_name}", None)
        if handler is not None:
            handler(content.get("data"), buffers)


def component_html(
    html_path: str,
    tags: dict[str, Any] | None = None,
    to_json: dict[str, Callable[[Any, widgets.Widget], Any]] | None = None,
    from_json: dict[str, Callable[[Any, widgets.Widget], Any]] | None = None,
) -> Callable[[Callable[P, None]], Callable[P, solara.Element]]:
    """Create a native browser component from one HTML, CSS, and JavaScript file.

    ``html_path`` is resolved relative to the decorated Python function's file.
    The component file has one top-level ``<template>`` section, and may have
    one ``<style>`` and one ``<script type="module">`` section. CSS is scoped
    to this widget's Shadow DOM. The module may export ``mount`` to control an
    instance and return a cleanup function.

    Function arguments become synchronized widget properties. A ``children``
    argument accepts Python widget children, shown where the template has a
    default ``<slot>``.

    **How data moves:** Python passes a prop such as ``name`` to the browser.
    ``data-solara-text="name"`` displays it; ``data-solara-model="name"``
    connects a supported form control in both directions. When the browser
    changes that prop, Python's ``on_name`` callback runs. This is the native
    HTML equivalent of changing a synchronized prop in ``component_vue``; it
    does not use Vue's ``$emit``. Plain HTML attributes have no automatic
    connection to Python: use the explicit ``data-solara-*`` bindings below.

    For custom timing or validation, omit ``data-solara-model`` and use the
    optional module's ``set("name", value)`` inside a DOM event listener. A
    JavaScript variable can hold a draft locally until that call. Text inputs
    with ``data-solara-model`` synchronize on every ``input`` event.

    A separate ``event_reset`` argument declares a discrete Python callback.
    ``data-solara-event-click="reset"`` invokes it from a button. The module's
    ``emit("reset", data)`` invokes the same callback with a JSON payload;
    this is a Solara widget message, not Vue's ``$emit``. Use prop changes and
    ``on_<prop>`` for state; use ``event_<name>`` for actions. An action does
    not change a prop unless its Python callback updates state.

    Template bindings use ``data-solara-text``, ``data-solara-attr-*``,
    ``data-solara-prop-*``, ``data-solara-model``, and
    ``data-solara-event-*``. Values are inserted as text or safe DOM attributes
    and properties; this is ordinary HTML rather than Vue syntax.

    Shared CSS and JavaScript in the app's public directory can be imported as
    ``../public/file.css`` and ``../public/file.js`` from component sections.
    The same spelling works for literal URL attributes in the template.

    This component view is supported in standalone Solara apps. It coexists
    with existing Vue components and does not change the default page shell.

    Example::

        @solara.component_html("greeting.html")
        def Greeting(name="World", on_name=None, event_reset=None, children=None):
            pass

    In ``greeting.html``, ``<input data-solara-model="name">`` updates
    ``name`` and calls ``on_name`` in Python, while
    ``<button data-solara-event-click="reset">Reset</button>`` calls
    ``event_reset``. The examples page contains a complete component file.

    ``tags``, ``to_json``, and ``from_json`` customize trait metadata and
    serialization in the same way as :func:`component_vue`.
    """

    def decorator(func: Callable[P, None]):
        source_path = os.path.abspath(inspect.getfile(func))
        resolved_path = os.path.abspath(os.path.join(os.path.dirname(source_path), html_path))
        try:
            with open(resolved_path, encoding="utf-8") as file:
                sections = parse_component_html(file.read(), resolved_path)
        except OSError as error:
            raise OSError(f"{resolved_path}: unable to read HTML component: {error}") from error

        signature = inspect.signature(func)
        parameters = signature.parameters
        reserved = {"template", "css_asset", "script_asset", "prop_names", "event_names", "_event_callbacks"}
        conflicting = reserved.intersection(parameters)
        if conflicting:
            raise ValueError("{}: reserved HTML component argument(s): {}".format(resolved_path, ", ".join(sorted(conflicting))))
        event_names = [name[6:] for name in parameters if name.startswith("event_")]
        prop_names = [
            name for name in parameters if not name.startswith("event_") and not (name.startswith("on_") and name[3:] in parameters) and name != "children"
        ]
        trait_tags = dict(tags or {})
        children_tags = {
            "to_json": widgets.widget_serialization["to_json"],
            "from_json": widgets.widget_serialization["from_json"],
        }
        children_tags.update(trait_tags.get("children", {}))
        trait_tags["children"] = children_tags
        widget_class = widget_from_signature(
            "SolaraHTMLComponentWidget",
            HTMLComponentWidget,
            func,
            "html_",
            tags=trait_tags,
            to_json=to_json or {},
            from_json=from_json or {},
        )
        # The base widget exposes children even when it is omitted from the
        # function signature, so Reacton can compose it with Python widgets.
        widget_class._html_event_names = tuple(event_names)

        template = sections.template
        css_filename = _register_asset(sections.css, "css")
        script_filename = _register_asset(sections.script, "js")

        def wrapper(*args, **kwargs):
            values = dict(signature.bind(*args, **kwargs).arguments)
            event_callbacks = {}
            for event_name in event_names:
                argument_name = f"event_{event_name}"
                if argument_name in values:
                    event_callbacks[event_name] = values.pop(argument_name)
            if event_callbacks:
                values["_event_callbacks"] = event_callbacks
            values.update(
                template=template,
                css_asset=css_filename,
                script_asset=script_filename,
                prop_names=prop_names,
                event_names=event_names,
            )
            return widget_class.element(**values)

        return wrapper

    return decorator


_component_html = component_html
