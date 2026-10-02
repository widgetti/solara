from __future__ import annotations

import functools
import inspect
import json
from pathlib import Path
from typing import Any, Callable

import ipyreact
import traitlets
from solara.server.reload import watch_file

from solara_html.imports import define_imports, module_name
from solara_html.parse import ComponentFile, parse_component_file

RUNTIME_MODULE = "solara-html"

# Defined once, before any component module, so those can import it by name.
ipyreact.define_module(RUNTIME_MODULE, Path(__file__).parent / "runtime.js")


def component_html(path: str) -> Callable[[Callable[..., None]], Callable[..., Any]]:
    """Turn a function signature plus a single-file HTML component into a Solara component.

    The path is relative to the file of the decorated function.
    A change to that file, or to a file its script imports, reloads the app.
    """

    def decorator(func: Callable[..., None]) -> Callable[..., Any]:
        signature = inspect.signature(func)
        component_path = (Path(inspect.getfile(func)).parent / path).resolve()
        watch_file(component_path)
        # Imported files are defined first, because a module can only import modules defined before it.
        code = define_imports(_module_code(parse_component_file(component_path)), component_path)
        module = module_name(code)
        ipyreact.define_module(module, code=code)
        widget_class = _widget_from_signature(func.__name__ + "Widget", signature)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            values = dict(bound.arguments)
            if "children" in values and values["children"] is None:
                values["children"] = []  # ipyreact's children trait is a List
            # ipyreact passes each entry to React as a callable prop, named without the event_ prefix.
            events = {name[len("event_") :]: values.pop(name) for name in list(values) if name.startswith("event_")}
            # Reacton adds .element to widget classes at runtime
            return widget_class.element(_module=module, _type="Component", events=events, **values)  # type: ignore[attr-defined]

        return wrapper

    return decorator


def _widget_from_signature(class_name: str, signature: inspect.Signature) -> type:
    """An ipyreact widget class with one synced trait per prop.

    ipyreact passes each trait to React as a prop, with a set<Name> setter.
    Two arguments that give the same React prop name are rejected, because one would hide the other.
    """
    properties = {}
    react_names: dict[str, str] = {}  # React prop name -> the argument that gives it

    def claim(react_name: str, argument: str) -> None:
        if react_name in react_names:
            raise ValueError(f"{class_name}: arguments {react_names[react_name]!r} and {argument!r} both give the React prop {react_name!r}")
        react_names[react_name] = argument

    for name in signature.parameters:
        if name == "children":
            continue  # ipyreact already has children
        if name.startswith("event_"):
            claim(name[len("event_") :], name)  # ipyreact already has events
            continue
        if name.startswith("on_") and name[len("on_") :] in signature.parameters:
            continue  # Reacton calls on_<prop> when <prop> changes
        if name.startswith("_") or hasattr(ipyreact.Widget, name):
            raise ValueError(f"{class_name}: argument {name!r} clashes with an ipyreact.Widget attribute")
        claim(name, name)
        claim("set" + name[0].upper() + name[1:], name)
        properties[name] = traitlets.Any().tag(sync=True)
    return type(class_name, (ipyreact.Widget,), properties)


def _module_code(component: ComponentFile) -> str:
    """The component's own script, plus an export that hands its parts to the runtime.

    Imports are hoisted, so appending one after the user's code is valid.
    """
    return f"""{component.script or ""}
import {{ defineHtmlComponent }} from "{RUNTIME_MODULE}";
export const Component = defineHtmlComponent({{
  template: {json.dumps(component.template)},
  css: {json.dumps(component.css)},
  mount: typeof mount === "function" ? mount : null,
}});
"""
