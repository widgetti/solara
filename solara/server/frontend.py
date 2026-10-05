"""Frontend features: the parts of the browser bundle a Solara server page preloads.

Set with ``solara run --frontend``, ``SOLARA_FRONTEND`` or ``solara.server.settings.main.frontend``.
The value is a preset (``full`` or ``minimal``) followed by ``+feature`` or ``-feature``, for example
``minimal,+katex`` or ``full,-mermaid``. A feature that is not preloaded still works: the browser loads
it on first use, and the server logs one warning per feature that names the flag to add. The fonts and
icon sets are the exception: they never load on demand. Vuetify (and the mdi icons it needs) is always on.
Roboto comes with vuetify, but an app with its own font can leave it out with ``-roboto``. Vuetify's
stylesheet (vuetify-css) also comes with vuetify, and an app that brings its own Vuetify CSS leaves it out
with ``-vuetify-css``.

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
from typing import Dict, FrozenSet, Iterable, Optional, Set, Tuple

import ipyvue

from solara.server import settings

logger = logging.getLogger("solara.server.frontend")
# The solara logger is at ERROR level under `solara run`, but these warnings tell the user
# which flag to add, so they must show up. A level that is already set (solara run --log-level
# configures logging before the server imports this module) stays.
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)

vue3 = ipyvue.__version__.startswith("3")

FEATURES: Tuple[str, ...] = (
    "vuetify",
    "vuetify-css",
    "mdi",
    "material-icons",
    "roboto",
    "font-awesome",
    "lumino",
    "jupyter-controls",
    "jupyter-css",
    "output-widget",
    "katex",
    "mermaid",
    "vue-sfc",
)
REQUIRES: Dict[str, FrozenSet[str]] = {
    # Vuetify's icons use mdi
    "vuetify": frozenset({"mdi"}),
    # the controls (e.g. Tab uses Lumino's TabBar) and the Output widget use Lumino beyond what the core has
    "jupyter-controls": frozenset({"jupyter-css", "lumino"}),
    "output-widget": frozenset({"jupyter-css", "lumino"}),
}
# Features that come with a feature, unless the setting turns them off by name. Unlike REQUIRES, the feature
# works without them: Vuetify's typography (e.g. the caption and font-weight-light classes) assumes the Roboto
# font, but an app with its own font can leave Roboto out, for example with 'minimal,-roboto'. In the
# same way, an app that ships its own Vuetify CSS (e.g. built from Vuetify's SASS) leaves out Vuetify's
# stylesheet with '-vuetify-css'.
COMES_WITH: Dict[str, FrozenSet[str]] = {
    "vuetify": frozenset({"roboto", "vuetify-css"}),
}
PRESETS: Dict[str, FrozenSet[str]] = {
    # vuetify-css is not in full by itself, it comes with vuetify (COMES_WITH)
    "full": frozenset(FEATURES) - {"vuetify-css"},
    "minimal": frozenset(),
}
DEFAULT = "full"
# widget module (_model_module or _view_module) -> the feature it needs
MODULE_FEATURE: Dict[str, str] = {
    "@jupyter-widgets/controls": "jupyter-controls",
    "@jupyter-widgets/output": "output-widget",
}
# lumino has no check at widget creation: only a requirejs request for a module of the lumino chunk (for
# example @phosphor/widgets, by a widget of an nbextension) loads it, which the server cannot know.
# The browser reports that load (log_lazy_load).
# Features each build can leave out (key: Vue 3). Both builds keep Vuetify and what it needs (mdi): the page
# shell and the default layout are made of Vuetify. The Vue 2 build has no vue-sfc chunk. Other features are
# forced on. Vuetify's CSS (vuetify-css) is a file of its own, so it can be left out.
CAN_DISABLE: Dict[bool, FrozenSet[str]] = {
    True: frozenset(FEATURES) - {"vuetify", *REQUIRES["vuetify"]},
    False: frozenset(FEATURES) - {"vuetify", *REQUIRES["vuetify"], "vue-sfc"},
}
HELP = "Use a preset (full, minimal) followed by +feature or -feature, for example 'minimal,+katex' or 'full,-mermaid'."


@dataclasses.dataclass(frozen=True)
class Frontend:
    spec: str  # normalized, e.g. "minimal,+katex"
    features: FrozenSet[str]
    # the features the spec turns off by name (e.g. "-roboto"): they do not come with another feature (COMES_WITH)
    off: FrozenSet[str] = frozenset()

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


def _with_companions(features: Iterable[str], off: FrozenSet[str]) -> FrozenSet[str]:
    """features, what they need, and what comes with them (COMES_WITH) unless it is in off."""
    result = set(_closure(features))
    for feature in list(result):
        result |= COMES_WITH.get(feature, frozenset()) - off
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
    for needed in sorted(removed):
        # every feature that is on and needs it, so that the suggested value works
        users = sorted(feature for feature in features if needed in REQUIRES.get(feature, frozenset()))
        if users:
            names = " and ".join(repr(user) for user in users)
            off = ",".join(f"-{name}" for name in [*users, needed])
            raise ValueError(
                f"Invalid frontend setting {value!r}: {names} {'needs' if len(users) == 1 else 'need'} {needed!r}, "
                f"so '-{needed}' cannot be used while {'it is' if len(users) == 1 else 'they are'} on. "
                f"Also turn off {names} ('{off}'), or keep {needed!r}."
            )
    return Frontend(spec=",".join(normalized), features=_with_companions(features, frozenset(removed)), off=frozenset(removed))


def effective(frontend: Frontend, vue3: bool, fontawesome_enabled: bool = True) -> Frontend:
    """The features this build really uses: some cannot be left out (vuetify, mdi), vue-sfc is Vue 3 only.

    fontawesome_enabled=False (SOLARA_ASSETS_FONTAWESOME_ENABLED=false) is an alias for -font-awesome.
    """
    features = set(frontend.features)
    all_features = set(FEATURES)
    if not vue3:
        features.discard("vue-sfc")  # there is no vue-sfc chunk on Vue 2
        all_features.discard("vue-sfc")
    forced = all_features - features - CAN_DISABLE[vue3]
    # a preset (minimal) leaves them out silently, a '-vuetify' or '-mdi' in the spec warns
    if forced & frontend.off:
        logger.warning(
            "The %s build cannot leave out %s, so they stay on. Vuetify is always on, and Vuetify needs the mdi icons.",
            "Vue 3" if vue3 else "Vue 2",
            ", ".join(sorted(forced & frontend.off)),
        )
    features |= forced
    if not fontawesome_enabled:
        features.discard("font-awesome")
    # a forced Vuetify brings Roboto and Vuetify's CSS, unless the spec says '-roboto' or '-vuetify-css'
    return Frontend(spec=frontend.spec, features=_with_companions(features, frontend.off), off=frontend.off)


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


# A page sends the spec of the server (normalized), which is far shorter. The spec and the features come from
# the browser and show up in the process-wide warnings, so a longer value is not a page's.
_MAX_PAGE_SPEC = 256


def from_page(value) -> Optional[Frontend]:
    """The frontend a page preloaded (its window.solaraFrontend, which the page sends with run), or None."""
    if not isinstance(value, dict):
        return None
    spec, features = value.get("spec"), value.get("features")
    if not isinstance(spec, str) or not isinstance(features, list):
        return None
    if len(spec) > _MAX_PAGE_SPEC or len(features) > len(FEATURES):
        return None
    try:
        # the browser sends it: keep only known names, the spec shows up in the warnings
        spec = parse(spec).spec
    except ValueError:
        return None
    return Frontend(spec=spec, features=frozenset(feature for feature in features if feature in FEATURES))


def _context_frontend() -> Optional[Frontend]:
    """In a virtual kernel context: the frontend of its page (see active), otherwise None."""
    kernel_context = sys.modules.get("solara.server.kernel_context")
    if kernel_context is None or not kernel_context.has_current_context():
        return None
    return kernel_context.get_current_context().frontend or current()


def active() -> Frontend:
    """The features of the page of the current virtual kernel context, otherwise the server setting.

    The run message pins the page's features on the kernel context, so the server keeps building
    widgets for the page it has, also when a hot reload changes solara.server.settings.main.frontend.
    """
    return _context_frontend() or current()


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
    frontend = _context_frontend()
    if frontend is None or feature in frontend:
        return
    _warn_once(feature, what, frontend)


# a requirejs module name, as the browser reports it (it shows up in the warning)
_MODULE_RE = re.compile(r"[@\w./-]{1,100}", re.ASCII)


def log_lazy_load(feature: str, module: Optional[str] = None) -> None:
    """The browser lazy loaded a feature (the frontend-lazy-load message on the control comm).

    module is the requirejs module that asked for it, if any (for example '@phosphor/widgets' for lumino).
    """
    if feature not in FEATURES:
        logger.debug("unknown frontend feature lazy loaded: %r", feature)
        return
    frontend = active()
    if feature in frontend:
        return
    what = f"The requirejs module {module!r} of the page" if isinstance(module, str) and _MODULE_RE.fullmatch(module) else "The page"
    _warn_once(feature, what, frontend)


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
def _nothing_to_check(features: FrozenSet[str]) -> bool:
    return all(feature in features for feature in MODULE_FEATURE.values()) and (not vue3 or "vue-sfc" in features or not _vue_sfc_chunk_exists())


def check_widget(widget) -> None:
    """Log one warning per feature per process when a widget needs a feature that is not preloaded.

    Called for each widget that is created in a virtual kernel context (see solara.server.patch).
    """
    frontend = active()
    if _nothing_to_check(frontend.features):
        return
    feature = missing_feature(widget, frontend)
    if feature is None:
        return
    cls = type(widget)
    _warn_once(feature, f"The widget {cls.__module__}.{cls.__name__}", frontend)
