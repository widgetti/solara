"""Frontend features: the parts of the browser bundle a Solara server page preloads.

Set with ``solara run --frontend``, ``SOLARA_FRONTEND`` or ``solara.server.settings.main.frontend``.
The value is a preset (``full`` or ``minimal``) followed by ``+feature`` or ``-feature``, for example
``minimal,+katex`` or ``full,-mermaid``. A feature that is not preloaded still works: the browser loads
it on first use, and the server logs one warning per feature that names the flag to add. The fonts and
icon sets (material-icons, roboto, font-awesome) are the exception: they never load on demand.

This module does not parse the setting at import time: Jupyter ignores the setting, and a bad value
must not break ``import solara`` there. The CLI and solara.server.starlette check it early instead.
"""

import dataclasses
import difflib
import logging
import re
import sys
import threading
from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, Optional, Set, Tuple, Type, TypeVar

import ipyvue

from solara.server import settings

logger = logging.getLogger("solara.server.frontend")
# The solara logger is at ERROR level under `solara run`, but these warnings tell the user
# which flag to add, so they must show up.
logger.setLevel(logging.WARNING)

vue3 = ipyvue.__version__.startswith("3")

FEATURES: Tuple[str, ...] = (
    "vuetify",
    "mdi",
    "material-icons",
    "roboto",
    "font-awesome",
    "jupyter-controls",
    "jupyter-css",
    "output-widget",
    "katex",
    "mermaid",
    "vue-sfc",
)
REQUIRES: Dict[str, FrozenSet[str]] = {
    "vuetify": frozenset({"mdi"}),
    "jupyter-controls": frozenset({"jupyter-css"}),
    "output-widget": frozenset({"jupyter-css"}),
}
PRESETS: Dict[str, FrozenSet[str]] = {
    "full": frozenset(FEATURES),
    "minimal": frozenset(),
}
DEFAULT = "full"
# widget module (_model_module or _view_module) -> the feature it needs
MODULE_FEATURE: Dict[str, str] = {
    "jupyter-vuetify": "vuetify",
    "@jupyter-widgets/controls": "jupyter-controls",
    "@jupyter-widgets/output": "output-widget",
}
# Features each build can leave out (key: Vue 3). The Vue 2 build keeps Vuetify (and mdi, which
# Vuetify needs) in its core bundle, and has no vue-sfc chunk. Other features are forced on.
CAN_DISABLE: Dict[bool, FrozenSet[str]] = {
    True: frozenset(FEATURES),
    False: frozenset(FEATURES) - {"vuetify", "mdi", "vue-sfc"},
}
HELP = "Use a preset (full, minimal) followed by +feature or -feature, for example 'minimal,+katex' or 'full,-mermaid'."


@dataclasses.dataclass(frozen=True)
class Frontend:
    spec: str  # normalized, e.g. "minimal,+katex"
    features: FrozenSet[str]

    def __contains__(self, feature: str) -> bool:
        return feature in self.features

    def suggest(self, feature: str) -> str:
        """The setting value that also preloads feature (and what it needs)."""
        return f"{self.spec},+{feature}"

    def to_js(self) -> Dict:
        """What the page passes to the browser (window.solaraFrontend)."""
        return {"spec": self.spec, "features": sorted(self.features)}


def _closure(features: Iterable[str]) -> FrozenSet[str]:
    result = set(features)
    todo = list(result)
    while todo:
        for needed in REQUIRES.get(todo.pop(), ()):
            if needed not in result:
                result.add(needed)
                todo.append(needed)
    return frozenset(result)


def _unknown(name: str, value: str) -> ValueError:
    close = difflib.get_close_matches(name, [*PRESETS, *FEATURES], n=1)
    hint = f" Did you mean {close[0]!r}?" if close else ""
    return ValueError(f"Invalid frontend setting {value!r}: unknown preset or feature {name!r}.{hint} {HELP} Features: {', '.join(FEATURES)}.")


def parse(value: str) -> Frontend:
    """Parse a --frontend value, raise ValueError with a helpful message for a bad value."""
    tokens = [token.strip().lower().replace("_", "-") for token in value.split(",")]
    tokens = [token for token in tokens if token]
    preset = DEFAULT
    if tokens and tokens[0][0] not in "+-":
        preset = tokens.pop(0)
        if preset in FEATURES:
            raise ValueError(f"Invalid frontend setting {value!r}: write '+{preset}' to turn {preset!r} on, or '-{preset}' to turn it off. {HELP}")
        if preset not in PRESETS:
            raise _unknown(preset, value)
    features = set(PRESETS[preset])
    removed: Set[str] = set()
    normalized = [preset]
    for token in tokens:
        sign, name = token[0], token[1:].strip()
        if sign not in "+-":
            if token in PRESETS:
                raise ValueError(f"Invalid frontend setting {value!r}: the preset {token!r} must come first. {HELP}")
            if token in FEATURES:
                raise ValueError(f"Invalid frontend setting {value!r}: write '+{token}' to turn {token!r} on, or '-{token}' to turn it off.")
            raise _unknown(token, value)
        if name in PRESETS:
            raise ValueError(f"Invalid frontend setting {value!r}: the preset {name!r} must come first, without '+' or '-'. {HELP}")
        if name not in FEATURES:
            raise _unknown(name, value)
        if sign == "+":
            features |= _closure([name])
            removed -= _closure([name])
        else:
            features.discard(name)
            removed.add(name)
        normalized.append(sign + name)
    for feature in sorted(features):
        conflict = REQUIRES.get(feature, frozenset()) & removed
        if conflict:
            needed = sorted(conflict)[0]
            raise ValueError(
                f"Invalid frontend setting {value!r}: {feature!r} needs {needed!r}, so '-{needed}' cannot be used while {feature!r} is on. "
                f"Also turn off {feature!r} ('-{feature},-{needed}'), or keep {needed!r}."
            )
    return Frontend(spec=",".join(normalized), features=_closure(features))


def effective(frontend: Frontend, vue3: bool, fontawesome_enabled: bool = True) -> Frontend:
    """The features this build really uses: some cannot be left out (Vue 2), vue-sfc is Vue 3 only.

    fontawesome_enabled=False (SOLARA_ASSETS_FONTAWESOME_ENABLED=false) is an alias for -font-awesome.
    """
    features = set(frontend.features)
    all_features = set(FEATURES)
    if not vue3:
        features.discard("vue-sfc")  # there is no vue-sfc chunk on Vue 2
        all_features.discard("vue-sfc")
    forced = all_features - features - CAN_DISABLE[vue3]
    if forced:
        logger.warning("The %s build cannot leave out %s, so they stay on.", "Vue 3" if vue3 else "Vue 2", ", ".join(sorted(forced)))
        features |= forced
    if not fontawesome_enabled:
        features.discard("font-awesome")
    return Frontend(spec=frontend.spec, features=_closure(features))


@lru_cache(maxsize=None)
def _current(value: str, fontawesome_enabled: bool, vue3: bool) -> Frontend:
    return effective(parse(value), vue3, fontawesome_enabled)


def current(vue3: Optional[bool] = None) -> Frontend:
    """The effective features of this server (reads the settings on every call, cached per value)."""
    return _current(settings.main.frontend, settings.assets.fontawesome_enabled, _vue3() if vue3 is None else vue3)


def legacy(vue3: Optional[bool] = None) -> Frontend:
    """Full, as on Solara before --frontend existed (the Jupyter popout page and the pyodide build)."""
    return _current(DEFAULT, settings.assets.fontawesome_enabled, _vue3() if vue3 is None else vue3)


def _vue3() -> bool:
    # read the module attribute at call time, so tests can monkeypatch it
    return vue3


def vuetify_enabled() -> bool:
    """False only on a Solara server that runs without the vuetify feature.

    Outside a virtual kernel context (Jupyter, or import time) this is always True, so Jupyter never changes.
    """
    kernel_context = sys.modules.get("solara.server.kernel_context")
    if kernel_context is None or not kernel_context.has_current_context():
        return True
    return "vuetify" in current()


T = TypeVar("T")


def template_class(vuetify_class: Type[T], vue_class: Type[T]) -> Type[T]:
    """The widget class for a solara template that has no Vuetify tags.

    vuetify_class (a VuetifyTemplate, as before) unless this server runs without the vuetify feature, then
    vue_class (an ipyvue.VueTemplate with the same traits), so the page does not need Vuetify.
    """
    return vuetify_class if vuetify_enabled() else vue_class


_warned: Set[str] = set()
_warned_lock = threading.Lock()


def _warn_once(feature: str, what: str, frontend: Frontend) -> None:
    with _warned_lock:
        if feature in _warned:
            return
        _warned.add(feature)
    # 'Add "+feature" to --frontend (SOLARA_FRONTEND) to preload it.' is also the wording of the browser
    # console warning (solara-widget-manager features.ts), and tests/benchmark/summary.py searches for it
    logger.warning(
        "%s needs the frontend feature %r, which this server does not preload. "
        "The browser loads it on first use, which slows down that first render. "
        'Add "+%s" to --frontend (SOLARA_FRONTEND) to preload it, for example --frontend=%s.',
        what,
        feature,
        feature,
        frontend.suggest(feature),
    )


def warn_missing(feature: str, what: str) -> None:
    """Log one warning per feature per process when feature is used but not preloaded.

    Only on a Solara server (a virtual kernel context exists): Jupyter loads everything.
    """
    if feature not in FEATURES:
        raise ValueError(f"Unknown frontend feature {feature!r}")
    kernel_context = sys.modules.get("solara.server.kernel_context")
    if kernel_context is None or not kernel_context.has_current_context():
        return
    frontend = current()
    if feature in frontend:
        return
    _warn_once(feature, what, frontend)


def warn_no_layout(component: str) -> None:
    """Log one warning per component per process when a Sidebar, AppBar or AppBarTitle has no layout to show it.

    Only when the vuetify feature is off: then Solara uses no default layout (AppLayout is made of Vuetify widgets).
    """
    if vuetify_enabled():
        return
    key = f"no-layout:{component}"
    with _warned_lock:
        if key in _warned:
            return
        _warned.add(key)
    logger.warning(
        "%s: its children are not shown, because no layout shows them. Without the frontend feature 'vuetify', Solara uses no "
        'default layout (AppLayout). Add "+vuetify" to --frontend (SOLARA_FRONTEND), or use solara.AppLayout or a Layout of your own.',
        component,
    )


def log_lazy_load(feature: str) -> None:
    """The browser lazy loaded a feature (the frontend-lazy-load message on the control comm)."""
    if feature not in FEATURES:
        logger.debug("unknown frontend feature lazy loaded: %r", feature)
        return
    frontend = current()
    if feature in frontend:
        return
    _warn_once(feature, "The page", frontend)


@lru_cache(maxsize=None)
def _vue_sfc_chunk_exists() -> bool:
    # ipyvue >= 3.1 ships the SFC compiler as a separate chunk; before, it is always in nodeps.js
    return (Path(ipyvue.__file__).parent / "nbextension" / "nodeps-vue-sfc.js").exists()


# Template features that ipyvue compiles only with the full SFC compiler (the vue-sfc chunk).
_SFC_ONLY = re.compile(r"<script[^>]*\bsetup\b|<style[^>]*\bscoped\b|lang=[\"']ts[\"']")


@lru_cache(maxsize=256)
def _template_needs_sfc(template: str) -> bool:
    return _SFC_ONLY.search(template) is not None


def _template_text(widget) -> Optional[str]:
    template = getattr(widget, "template", None)
    if template is not None and not isinstance(template, str):
        # an ipyvue.Template widget
        template = getattr(template, "template", None)
    return template if isinstance(template, str) else None


def missing_feature(widget, frontend: Frontend) -> Optional[str]:
    """The feature a widget needs that frontend does not preload, or None."""
    for module in (getattr(widget, "_model_module", None), getattr(widget, "_view_module", None)):
        feature = MODULE_FEATURE.get(module) if isinstance(module, str) else None
        if feature is not None and feature not in frontend:
            return feature
    if vue3 and "vue-sfc" not in frontend and _vue_sfc_chunk_exists():
        template = _template_text(widget)
        if template is not None and _template_needs_sfc(template):
            return "vue-sfc"
    return None


@lru_cache(maxsize=None)
def _nothing_to_check(frontend: Frontend) -> bool:
    return all(feature in frontend for feature in MODULE_FEATURE.values()) and (not vue3 or "vue-sfc" in frontend or not _vue_sfc_chunk_exists())


def check_widget(widget) -> None:
    """Log one warning per feature per process when a widget needs a feature that is not preloaded.

    Called for each widget that is created in a virtual kernel context (see solara.server.patch).
    """
    frontend = current()
    if _nothing_to_check(frontend):
        return
    feature = missing_feature(widget, frontend)
    if feature is None:
        return
    cls = type(widget)
    _warn_once(feature, f"The widget {cls.__module__}.{cls.__name__}", frontend)
