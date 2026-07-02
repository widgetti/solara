"""Derive stable, cross-process persistence keys from a reactive's definition site.

This module is intentionally standalone: it imports only the stdlib, ``executing``,
and two frame helpers from :mod:`solara.toestand`. It does not import the rest of
``solara.state``. See ``docs/design-redis-state-persistence.md`` §4.1 for the policy.

The two statically unambiguous patterns get an auto-derived key:

- module-level single-name assignment ``count = solara.reactive(0, persist=True)``
  (including annotated ``n: int = ...``) -> ``"<module>:count"`` (:func:`derive_key`);
- class attribute -> ``"<module>:Owner.attr"`` via :func:`derive_key_for_class_attribute`
  (wired from ``Reactive.__set_name__``).

Everything else raises :class:`PersistKeyError`, demanding an explicit ``key=``.
"""

import ast
import linecache
import logging
import os
import threading
import weakref
from typing import Any, Dict, Optional, Tuple

import executing

from solara.toestand import _find_outside_solara_frame, _is_internal_module

logger = logging.getLogger("solara.state")

# Node types that, as an ancestor of the assignment, make the definition site
# ambiguous (many instances) or conditional. ClassDef is refused here on purpose:
# the class-attribute case is handled by derive_key_for_class_attribute via __set_name__.
_FORBIDDEN_ANCESTORS = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.If,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.ClassDef,
)

_FIX_EXAMPLE = 'solara.reactive(..., persist=True, key=f"user:{user_id}:query")'
_NEVER_WARNING = "NEVER use a constant key for reactives created per-instance - instances would overwrite each other's state."


class PersistKeyError(ValueError):
    """A persistence key could not be safely derived, or two definition sites collide.

    Subclasses :class:`ValueError` so existing ``except ValueError`` handlers keep working.

    The ``reason`` attribute carries a stable machine-readable code for the refusal.
    ``REASON_CLASS_BODY`` is load-bearing: it tells ``Reactive.__init__`` that the
    definition is a class attribute, whose key is resolved later via ``__set_name__``
    instead of failing.
    """

    reason: str = "ambiguous"


REASON_CLASS_BODY = "class-body"


def _is_derive_module(file_name: str) -> bool:
    return file_name.split(os.sep)[-2:] == ["state", "derive.py"]


def _user_frame():
    # _find_outside_solara_frame() stops at the first frame outside toestand's skip-list,
    # which is derive_key's own frame (this module is not in that list). Continue skipping
    # this module and any internal frames until we reach real user code.
    frame = _find_outside_solara_frame()
    while frame is not None and (_is_internal_module(frame.f_code.co_filename) or _is_derive_module(frame.f_code.co_filename)):
        frame = frame.f_back
    return frame


# executing caches its Source (and thus the module tree object) per file for the process
# lifetime, so caching the parent map per tree turns per-derivation O(module size) into a
# one-time cost per module - matters when a module declares many persisted reactives.
_parent_map_cache: Dict[int, Tuple[ast.AST, Dict[ast.AST, ast.AST]]] = {}


def _build_parent_map(tree: ast.AST) -> Dict[ast.AST, ast.AST]:
    cached = _parent_map_cache.get(id(tree))
    if cached is not None:
        return cached[1]
    parents: Dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    # keep a strong ref to tree so its id() cannot be reused by a different object
    _parent_map_cache[id(tree)] = (tree, parents)
    return parents


def _site(frame, node) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    if frame is None:
        return None, None, None
    filename = frame.f_code.co_filename
    lineno = getattr(node, "lineno", None) or frame.f_lineno
    line = linecache.getline(filename, lineno).strip() or None
    return filename, lineno, line


def _refuse(reason: str, frame, node, *, hint: str = "", code: str = "ambiguous") -> PersistKeyError:
    filename, lineno, line = _site(frame, node)
    site = "<unknown location>" if filename is None else f"{filename}:{lineno}"
    if line:
        site += f": `{line}`"
    parts = [
        f"persist=True requires an explicit key= here: {reason}",
        f"Definition site: {site}",
    ]
    if hint:
        parts.append(hint)
    parts.append(f"Give each instance a unique key, e.g.:  {_FIX_EXAMPLE}")
    parts.append(_NEVER_WARNING)
    error = PersistKeyError("\n".join(parts))
    error.reason = code
    return error


def _target_name(node: ast.AST, parent: Optional[ast.AST], frame) -> str:
    # single-target Assign with one Name, or AnnAssign with a Name target
    if isinstance(parent, ast.Assign):
        if len(parent.targets) != 1:
            raise _refuse(
                "a chained assignment (a = b = ...) binds one reactive to several names, so the intended key is ambiguous.",
                frame,
                node,
            )
        target = parent.targets[0]
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            raise _refuse(
                "this reactive is assigned to an attribute, not a bare module-level name; an attribute target is not a stable key.",
                frame,
                node,
            )
        if isinstance(target, (ast.Tuple, ast.List)):
            raise _refuse(
                "a tuple/list-unpacking assignment does not map this reactive to a single stable name.",
                frame,
                node,
            )
        raise _refuse(
            "this reactive is not assigned to a plain module-level name, so there is no name to key on.",
            frame,
            node,
        )
    if isinstance(parent, ast.AnnAssign):
        if isinstance(parent.target, ast.Name):
            return parent.target.id
        if isinstance(parent.target, ast.Attribute):
            raise _refuse(
                "this reactive is assigned to an attribute, not a bare module-level name; an attribute target is not a stable key.",
                frame,
                node,
            )
        raise _refuse(
            "this reactive is not assigned to a plain module-level name, so there is no name to key on.",
            frame,
            node,
        )
    if isinstance(parent, ast.Tuple):
        raise _refuse(
            "a tuple assignment does not map this reactive to a single stable name.",
            frame,
            node,
        )
    # parent is a List / Call / other expression: the reactive lives in a container or as
    # a call argument, not directly assigned to a name.
    raise _refuse(
        "this reactive is not assigned to a module-level name (it appears inside a container or as a call argument), so it has no name to key on.",
        frame,
        node,
    )


def _check_ancestors(node: ast.AST, parents: Dict[ast.AST, ast.AST], frame) -> None:
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, ast.ClassDef):
            raise _refuse(
                "this reactive is defined in a class body.",
                frame,
                node,
                hint="Class attributes get an automatic, stable key via __set_name__ (module:Owner.attr); no key= is needed there.",
                code=REASON_CLASS_BODY,
            )
        if isinstance(cur, (ast.For, ast.AsyncFor, ast.While)):
            raise _refuse(
                "a reactive created inside a loop produces one instance per iteration; instances cannot share a key.",
                frame,
                node,
            )
        if isinstance(cur, (ast.If, ast.With, ast.AsyncWith, ast.Try)):
            raise _refuse(
                "a reactive created inside a conditional (if/with/try) is not a stable, unconditional module-level definition.",
                frame,
                node,
            )
        if isinstance(cur, _FORBIDDEN_ANCESTORS):
            # FunctionDef/Lambda/comprehension reached without a dedicated frame (e.g. an
            # inlined comprehension on Python 3.12+); treat as a per-call/per-item factory.
            raise _refuse(
                "a reactive created inside a function or factory produces one instance per call; instances cannot share a key.",
                frame,
                node,
            )


def derive_key() -> str:
    """Derive a stable persistence key from the module-level definition site.

    Walks to the user frame, resolves the exact ``reactive(...)`` call via ``executing``,
    and requires a module-level single-name assignment. Raises :class:`PersistKeyError`
    (a ``ValueError``) with an actionable message on anything ambiguous.
    """
    frame = _user_frame()
    if frame is None:
        raise _refuse(
            "the definition site could not be located in the call stack.",
            None,
            None,
        )

    node = None
    tree = None
    try:
        ex = executing.Source.executing(frame)
        node = ex.node
        tree = ex.source.tree
    except Exception:
        node = None
        tree = None
    if node is None or tree is None:
        # a class/function body frame has a non-"<module>" co_name; without a resolved node
        # we cannot give the precise reason, but we know it is not a clean module-level def
        if frame.f_code.co_name != "<module>":
            raise _refuse(
                "a reactive created inside a function or factory produces one instance per call; instances cannot share a key.",
                frame,
                None,
            )
        raise _refuse(
            "the source of the definition site is unavailable (e.g. a frozen app or exec'd string), so the key cannot be derived.",
            frame,
            None,
        )

    parents = _build_parent_map(tree)
    parent = parents.get(node)
    # a function/class/loop/conditional shows up as an ancestor in the module AST regardless
    # of the frame name, so check ancestors first: they take priority over the shape check
    _check_ancestors(node, parents, frame)
    name = _target_name(node, parent, frame)

    module_name = frame.f_globals.get("__name__")
    if not module_name:
        raise _refuse(
            "the module has no __name__, so a stable key cannot be derived.",
            frame,
            node,
        )

    key = f"{module_name}:{name}"
    filename, lineno, _ = _site(frame, node)
    logger.info('derived persistence key "%s" for %s:%s', key, filename, lineno)
    return key


def derive_key_for_class_attribute(owner: type, name: str) -> str:
    """Derive a stable key for a class-attribute reactive (the ``__set_name__`` path)."""
    key = f"{owner.__module__}:{owner.__qualname__}.{name}"
    logger.info('derived persistence key "%s" for class attribute %s.%s', key, owner.__qualname__, name)
    return key


# --- collision registry (process-global) ------------------------------------------------

_registry_lock = threading.Lock()
_registry: Dict[str, Tuple[Tuple[str, int, int], "weakref.ref"]] = {}


def _fmt_source(source: Tuple[str, int, int]) -> str:
    return f"{source[0]}:{source[1]}"


def register_persist_key(key: str, obj: Any, source: Tuple[str, int, int], derived: bool) -> None:
    """Register a persistence key against its owning reactive, catching collisions.

    Raises :class:`PersistKeyError` when ``key`` is already held by a *live* reactive from
    a *different* source location. Re-registration from the same source (hot reload) or
    over a dead reference is silently allowed. Applies to explicit keys too (``derived``
    only annotates intent for callers/logging).
    """
    with _registry_lock:
        existing = _registry.get(key)
        if existing is not None:
            old_source, old_ref = existing
            old_obj = old_ref()
            if old_obj is not None and old_obj is not obj and old_source != source:
                error = PersistKeyError(
                    f"persistence key {key!r} is already used by a reactive defined at "
                    f"{_fmt_source(old_source)}; a second reactive at {_fmt_source(source)} maps to the same key.\n"
                    "Two different definition sites cannot share a persistence key - their state would collide in the backend.\n"
                    'Give each an explicit unique key=, e.g.  solara.reactive(..., persist=True, key="myapp.unique_name")'
                )
                error.reason = "collision"
                raise error
        _registry[key] = (source, weakref.ref(obj))


def _reset_registry() -> None:
    """Clear the collision registry (tests only)."""
    with _registry_lock:
        _registry.clear()
