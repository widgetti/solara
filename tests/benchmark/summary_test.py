from typing import List

from tests.benchmark.summary import (
    BenchResult,
    ConfigResult,
    Visit,
    aggregate,
    compare,
    lazy_features,
    markdown_table,
    write_step_summary,
)


def make_visit(first_widget: float, **extra) -> Visit:
    visit: Visit = {
        "label": "run",
        "first_widget": first_widget,
        "dcl": 10.0,
        "ws_open": 20.0,
        "first_comm_open": 30.0,
        "session_start": 40.0,
        "script_ms": 50.0,
        "task_ms": 60.0,
        "requests": 7,
        "xfer_kb": 100.0,
        "raw_kb": 200.0,
        "errors": [],
        "warnings": [],
    }
    visit.update(extra)  # type: ignore
    return visit


def make_config(name: str, cold: List[float], throttled: bool = True) -> ConfigResult:
    app, _, preset = name.partition("@")
    runs = {"fast": {"cold": [make_visit(t) for t in cold], "warm": [make_visit(cold[0] / 2)]}}
    if throttled:
        runs["throttled"] = {"cold": [make_visit(t * 4) for t in cold], "warm": [make_visit(cold[0] * 2)]}
    config: ConfigResult = {"name": name, "app": app, "preset": preset, "idle_xfer_kb": 300.0, "lazy": ["vuetify"], "runs": runs}  # type: ignore
    config["median"] = {profile: {"cold": aggregate(r["cold"]), "warm": aggregate(r["warm"])} for profile, r in config["runs"].items()}
    return config


def make_result(configs: List[ConfigResult]) -> BenchResult:
    meta = {
        "solara": "1.0.0",
        "git_sha": "abc",
        "vue": "3",
        "throttle": {"latency_ms": 150, "down_mbit": 9, "up_mbit": 1.5, "cpu": 4},
        "loadavg_start": 1.234,
        "loadavg_end": 2.0,
    }
    return {"schema": 1, "meta": meta, "configs": configs}


def test_aggregate_median_and_range():
    visits = [
        make_visit(100.0, ws_open=None),
        make_visit(300.0, ws_open=None),
        make_visit(200.0, ws_open=None, errors=["boom"]),
        {"label": "x", "error": "timeout"},
    ]
    result = aggregate(visits)  # type: ignore
    assert result["first_widget"] == 200.0
    assert result["first_widget_min"] == 100.0
    assert result["first_widget_max"] == 300.0
    assert result["n"] == 3
    assert result["failed"] == 1
    assert result["errors"] == 1
    assert result["ws_open"] is None
    assert result["requests"] == 7


def test_markdown_table_one_row_per_config_and_profile():
    ok = make_config("hello@full", [100.0, 200.0, 300.0])
    skipped: ConfigResult = {"name": "hello@minimal", "app": "hello", "preset": "minimal", "skipped": "preset not supported"}
    failed: ConfigResult = {"name": "dashboard@full", "app": "dashboard", "preset": "full", "failed": "server exited with code 1"}
    md = markdown_table(make_result([ok, skipped, failed]))
    assert md.count("#### Unthrottled") == 1
    assert md.count("#### Throttled: latency 150 ms, 9 Mbit/s down, 1.5 Mbit/s up, CPU 4x") == 1
    for name in ["hello@full", "hello@minimal", "dashboard@full"]:
        assert md.count(f"| {name} |") == 2, name
    assert "| hello@full | 200 (100-300) | 50 |" in md
    assert "| hello@full | 800 (400-1200) | 200 |" in md
    assert "skipped: preset not supported" in md
    assert "failed: server exited with code 1" in md
    assert "load 1.2 to 2.0" in md
    assert "Websocket frames are not throttled" in md
    # every row has as many cells as the header
    rows = [line for line in md.splitlines() if line.startswith("| ")]
    assert len({row.count(" | ") for row in rows}) == 1


def test_markdown_table_skips_empty_profile():
    md = markdown_table(make_result([make_config("hello@full", [100.0], throttled=False)]))
    assert "#### Unthrottled" in md
    assert "#### Throttled" not in md


def test_markdown_table_lists_failed_configs_of_a_profile_that_ran():
    # bench.py marks a config failed when every cold visit of a profile failed: its row must not disappear
    failed: ConfigResult = {"name": "hello@full", "app": "hello", "preset": "full", "failed": "every fast cold visit failed"}
    result = make_result([failed])
    result["meta"]["runs"] = {"fast": {"cold": 3, "warm": 3}, "throttled": {"cold": 0, "warm": 0}}
    md = markdown_table(result)
    assert "#### Unthrottled (3 cold, 3 warm visits)" in md
    assert "| hello@full | failed: every fast cold visit failed |" in md
    assert "#### Throttled" not in md


def test_compare_adds_delta_and_na_for_unmatched():
    base = make_result([make_config("hello@full", [200.0])])
    now = make_result([make_config("hello@full", [220.0]), make_config("dashboard@full", [500.0])])
    deltas = compare(now, base)
    assert deltas["fast"] == {"hello@full": 10.0, "dashboard@full": None}
    assert deltas["throttled"]["hello@full"] == 10.0
    md = markdown_table(now, base)
    assert "Δ cold" in md
    assert "| hello@full | 220 (220-220) | +10.0% |" in md
    assert "| dashboard@full | 500 (500-500) | n/a |" in md


def test_lazy_regex_lists_distinct_features():
    texts = [
        # the browser console (solara-widget-manager features.ts, and main-vuetify.js for vue-sfc)
        'solara: frontend feature "vuetify" was not preloaded, it loads now. Add "+vuetify" to --frontend (SOLARA_FRONTEND) to preload it.',
        'solara: frontend feature "vue-sfc" was not preloaded, it loads now (script setup). Add "+vue-sfc" to --frontend (SOLARA_FRONTEND) to preload it.',
        # the server log (solara.server.frontend._warn_once): the example names more features than the one that loaded
        "WARNING solara.server.frontend: The page needs the frontend feature 'jupyter-controls', which this server does not preload. "
        "The browser loads it on first use, which slows down that first render. "
        'Add "+jupyter-controls" to --frontend (SOLARA_FRONTEND) to preload it, for example --frontend=minimal,+katex,+jupyter-controls.',
        'solara: frontend feature "vuetify" was not preloaded, it loads now. Add "+vuetify" to --frontend (SOLARA_FRONTEND) to preload it.',
        # a requirejs request names the module that asked
        'solara: frontend feature "lumino" was not preloaded, it loads now for the requirejs module "@phosphor/widgets". '
        'Add "+lumino" to --frontend (SOLARA_FRONTEND) to preload it.',
        'Add "+unknown" to --frontend, Add "+vuetify-extra" to --frontend, x+mdi +mermaid',
        "no features here",
    ]
    assert lazy_features(texts) == ["jupyter-controls", "lumino", "vue-sfc", "vuetify"]
    assert lazy_features([]) == []


def test_step_summary_appends_when_env_set(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert not write_step_summary("nothing\n")
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    assert write_step_summary("first\n")
    assert write_step_summary("second\n")
    assert path.read_text() == "first\nsecond\n"
