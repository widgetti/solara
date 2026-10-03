"""Aggregation and markdown output for the page load benchmark (stdlib only).

bench.py writes the records below as JSON; this module turns them into medians and
markdown tables, so a JSON file from an older run can be compared without a browser.
"""

import os
import re
import statistics
from typing import Any, Dict, Iterable, List, Mapping, Optional, TypedDict, cast


class Visit(TypedDict, total=False):
    label: str
    error: str  # set when the visit failed, the metrics are then missing
    first_widget: float
    dcl: float
    ws_open: Optional[float]
    first_comm_open: Optional[float]
    session_start: Optional[float]
    script_ms: float
    task_ms: float
    requests: int
    xfer_kb: float
    raw_kb: float
    errors: List[str]
    warnings: List[str]


class ProfileRuns(TypedDict):
    cold: List[Visit]
    warm: List[Visit]


class ConfigResult(TypedDict, total=False):
    name: str
    app: str
    preset: str
    skipped: str
    failed: str
    idle_xfer_kb: Optional[float]
    lazy: List[str]
    server_log: str
    runs: Dict[str, ProfileRuns]
    # profile -> "cold"/"warm" -> metric -> value
    median: Dict[str, Dict[str, Dict[str, Optional[float]]]]


class BenchResult(TypedDict):
    schema: int
    meta: Dict[str, Any]
    configs: List[ConfigResult]


METRICS = ["first_widget", "dcl", "ws_open", "first_comm_open", "session_start", "script_ms", "task_ms", "requests", "xfer_kb", "raw_kb"]
PROFILES = ["fast", "throttled"]

# The features of the --frontend setting. A lazy load warning, in the browser console and in the
# server log, says 'Add "+katex" to --frontend (SOLARA_FRONTEND) to preload it.'
FEATURES = [
    "vuetify",
    "mdi",
    "material-icons",
    "roboto",
    "font-awesome",
    "jupyter-controls",
    "output-widget",
    "jupyter-css",
    "katex",
    "mermaid",
    "vue-sfc",
]
LAZY_RE = re.compile(r'Add "\+(' + "|".join(re.escape(f) for f in sorted(FEATURES, key=len, reverse=True)) + r')" to --frontend')


def lazy_features(texts: Iterable[str]) -> List[str]:
    """Sorted distinct feature names that the lazy load warnings in texts name."""
    found = set()
    for text in texts:
        found.update(LAZY_RE.findall(text))
    return sorted(found)


def aggregate(visits: List[Visit]) -> Dict[str, Optional[float]]:
    """Median of each metric over the visits that did not fail, plus the first widget range."""
    ok = [v for v in visits if not v.get("error")]
    result: Dict[str, Optional[float]] = {"n": float(len(ok)), "failed": float(len(visits) - len(ok))}
    for metric in METRICS:
        values = [float(x) for x in (cast(Mapping[str, Any], v).get(metric) for v in ok) if x is not None]
        result[metric] = round(statistics.median(values), 1) if values else None
    first = [v["first_widget"] for v in ok if v.get("first_widget") is not None]
    result["first_widget_min"] = min(first) if first else None
    result["first_widget_max"] = max(first) if first else None
    result["errors"] = float(sum(len(v.get("errors", [])) for v in visits))
    return result


def compare(result: BenchResult, base: BenchResult) -> Dict[str, Dict[str, Optional[float]]]:
    """Change in percent of the median cold first widget time, per profile and config.

    None when the config (or profile) is missing in one of the two results, or has no value.
    """
    base_by_name = {c["name"]: c for c in base["configs"]}
    deltas: Dict[str, Dict[str, Optional[float]]] = {}
    for profile in PROFILES:
        per_config: Dict[str, Optional[float]] = {}
        for config in result["configs"]:
            now = _cold_first_widget(config, profile)
            other = base_by_name.get(config["name"])
            before = _cold_first_widget(other, profile) if other is not None else None
            per_config[config["name"]] = None if now is None or not before else round((now - before) / before * 100, 1)
        deltas[profile] = per_config
    return deltas


def _cold_first_widget(config: ConfigResult, profile: str) -> Optional[float]:
    return config.get("median", {}).get(profile, {}).get("cold", {}).get("first_widget")


def throttle_label(throttle: Mapping[str, Any]) -> str:
    return f"latency {throttle['latency_ms']} ms, {throttle['down_mbit']} Mbit/s down, {throttle['up_mbit']} Mbit/s up, CPU {throttle['cpu']}x"


COLUMNS = [
    "config",
    "1st widget cold (min-max)",
    "warm",
    "DCL",
    "ws open",
    "1st comm_open",
    "session start cold/warm",
    "script",
    "req",
    "xfer KB",
    "raw KB",
    "idle KB",
    "lazy",
    "errors",
]


def _num(value: Optional[float]) -> str:
    return "-" if value is None else f"{value:.0f}"


def _row(config: ConfigResult, profile: str, delta: Optional[Dict[str, Optional[float]]]) -> Optional[List[str]]:
    name = config["name"]
    reason = config.get("skipped") or config.get("failed")
    cells: List[str]
    if reason:
        label = "skipped" if config.get("skipped") else "failed"
        cells = [name, f"{label}: {reason}"] + [""] * (len(COLUMNS) - 2)
    else:
        median = config.get("median", {}).get(profile)
        if not median or not median["cold"].get("n"):
            return None
        cold, warm = median["cold"], median["warm"]
        first = f"{_num(cold['first_widget'])} ({_num(cold['first_widget_min'])}-{_num(cold['first_widget_max'])})"
        session = f"{_num(cold['session_start'])}/{_num(warm.get('session_start'))}"
        idle = _num(config.get("idle_xfer_kb")) if profile == "fast" else "-"
        errors = (cold.get("errors") or 0) + (warm.get("errors") or 0)
        failed = (cold.get("failed") or 0) + (warm.get("failed") or 0)
        errors_cell = f"{errors:.0f}" + (f" ({failed:.0f} visits failed)" if failed else "")
        cells = [
            name,
            first,
            _num(warm.get("first_widget")),
            _num(cold["dcl"]),
            _num(cold["ws_open"]),
            _num(cold["first_comm_open"]),
            session,
            _num(cold["script_ms"]),
            _num(cold["requests"]),
            _num(cold["xfer_kb"]),
            _num(cold["raw_kb"]),
            idle,
            ", ".join(config.get("lazy", [])) or "-",
            errors_cell,
        ]
    if delta is not None:
        value = delta.get(name)
        cells.insert(2, "n/a" if value is None else f"{value:+.1f}%")
    return cells


def _has_profile(result: BenchResult, profile: str) -> bool:
    return any(config.get("median", {}).get(profile, {}).get("cold", {}).get("n") for config in result["configs"])


def header(meta: Mapping[str, Any]) -> str:
    def m(key: str) -> str:
        value = meta.get(key)
        return "?" if value is None else str(value)

    def load(key: str) -> str:
        value = meta.get(key)
        return "?" if value is None else f"{value:.1f}"

    lines = [
        "### Solara page load benchmark",
        "",
        f"solara {m('solara')} ({m('git_sha')}), Vue {m('vue')} (ipyvue {m('ipyvue')}, ipyvuetify {m('ipyvuetify')}), "
        f"ipywidgets {m('ipywidgets')}, solara-assets {meta.get('solara_assets') or 'not installed'}, Python {m('python')}",
        f"{m('platform')}, {m('cpus')} CPUs, load {load('loadavg_start')} to {load('loadavg_end')}, playwright {m('playwright')}, Chromium {m('chromium')}",
        f"bundle source: {m('bundle_source')}, main bundle {m('main_bundle_bytes')} B, frontend flag supported: {m('frontend_supported')}",
    ]
    return "\n".join(lines)


def markdown_table(result: BenchResult, base: Optional[BenchResult] = None) -> str:
    """One table per profile, one row per config (skipped and failed configs included)."""
    meta = result["meta"]
    deltas = compare(result, base) if base is not None else None
    parts = [header(meta), ""]
    titles = {"fast": "Unthrottled", "throttled": ("Throttled: " + throttle_label(meta["throttle"])) if meta.get("throttle") else "Throttled"}
    runs = meta.get("runs", {})
    for profile in PROFILES:
        if not _has_profile(result, profile):
            continue
        columns = list(COLUMNS)
        if deltas is not None:
            columns.insert(2, "Δ cold")
        counts = runs.get(profile)
        title = titles[profile] + (f" ({counts['cold']} cold, {counts['warm']} warm visits)" if counts else "")
        parts += [f"#### {title}", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        for config in result["configs"]:
            cells = _row(config, profile, deltas[profile] if deltas is not None else None)
            if cells is not None:
                parts.append("| " + " | ".join(cells) + " |")
        parts.append("")
    parts.append(
        "Times in ms from the document request, median over the cold visits (a new browser each). "
        "warm is a second visit in the same browser. Websocket frames are not throttled. "
        "req, xfer KB and raw KB count the requests that started before the first widget. "
        "idle KB is all bytes of the warm-up visit until the network was idle for 1 s."
        + (" Δ cold compares the cold first widget time with the base file." if deltas is not None else "")
    )
    return "\n".join(parts) + "\n"


def write_step_summary(markdown: str, environ: Optional[Mapping[str, str]] = None) -> bool:
    """Append to the GitHub job summary when GITHUB_STEP_SUMMARY is set; returns whether it wrote."""
    environ = os.environ if environ is None else environ
    path = environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return False
    with open(path, "a", encoding="utf-8") as f:
        f.write(markdown)
    return True
