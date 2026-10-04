"""Page load benchmark for the solara server.

Run it from the repo root (this is not a pytest test):

    python -m tests.benchmark.bench                       # the default configs
    python -m tests.benchmark.bench --configs all         # what CI runs
    python -m tests.benchmark.bench --quick --compare /tmp/solara-bench/base.json

A config is app@preset, e.g. dashboard@full. Each config gets its own `solara run`
subprocess (the preset is a per server setting), started from a temporary directory with
the SOLARA_* environment variables removed. Each cold visit uses a new Chromium; the warm
visit is a second page in the same browser. The main metric is the time from the document
request to the first visible widget (the app's detector text).

The CLI uses click instead of Typer: click is a solara-server dependency, Typer is in no CI lock file.
"""

import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from importlib.metadata import version
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, Sequence, Tuple

import click
from playwright.async_api import Browser, BrowserContext, CDPSession, ConsoleMessage, Playwright, ViewportSize, async_playwright

from solara.server.threaded import get_free_port

from tests.benchmark.summary import BenchResult, ConfigResult, ProfileRuns, Visit, aggregate, lazy_features, markdown_table, write_step_summary

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# app name -> (file in apps/, the text that marks the first visible widget)
APPS: Dict[str, Tuple[str, str]] = {
    "hello": ("hello.py", "Hello benchmark"),
    "dashboard": ("dashboard.py", "row-0"),
    "dashboard_lite": ("dashboard_lite.py", "row-0"),
}
PRESETS = ["full", "minimal"]
DEFAULT_CONFIGS = ["hello@full", "hello@minimal", "dashboard@full", "dashboard_lite@minimal"]
# dashboard@minimal: the lazy load path; dashboard_lite@full: separates the app effect from the preset effect
ALL_CONFIGS = DEFAULT_CONFIGS + ["dashboard@minimal", "dashboard_lite@full"]

THROTTLE = {"latency_ms": 150, "down_mbit": 9, "up_mbit": 1.5, "cpu": 4}
VIEWPORT: ViewportSize = {"width": 1280, "height": 800}
VISIT_TIMEOUT_MS = 60_000
SERVER_START_TIMEOUT = 60.0
WARMUP_ATTEMPTS = 2
WARM_SLEEP = 2.0  # the unload beacon closes the previous page's kernel, let that finish first
SETTLE_CAP = 3.0  # wait at most this long for the requests started before the first widget
IDLE_QUIET = 1.0
IDLE_CAP = 8.0

INIT_JS = r"""
(() => {
  const TEXT = %s;
  window.__fv = undefined;
  let scheduled = false;
  function check() {
    scheduled = false;
    if (window.__fv !== undefined) return;
    const r = document.evaluate("//*[not(self::script) and not(self::style)][text()[contains(., '" + TEXT + "')]]", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    for (let i = 0; i < r.snapshotLength; i++) {
      const el = r.snapshotItem(i);
      if (el.checkVisibility({opacityProperty: true, visibilityProperty: true})) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) { window.__fv = performance.now(); obs.disconnect(); return; }
      }
    }
  }
  const obs = new MutationObserver(() => { if (!scheduled) { scheduled = true; requestAnimationFrame(check); } });
  obs.observe(document, {subtree: true, childList: true, characterData: true, attributes: true});
})();
"""

# runs in the server's interpreter, cwd and env: that is the solara the server imports
PROBE_CODE = r"""
import json, platform
from importlib.metadata import PackageNotFoundError, version

def v(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None

import solara
import solara.util
import solara.server.settings as settings

print(json.dumps({
    "solara": solara.__version__,
    "solara_path": solara.__file__,
    "vue": "3" if solara.util.IPYVUETIFY_V3 else "2",
    "ipyvue": v("ipyvue"),
    "ipyvuetify": v("ipyvuetify"),
    "ipywidgets": v("ipywidgets"),
    "solara_assets": v("solara-assets"),
    "python": platform.python_version(),
    "platform": platform.platform(),
    "proxy_cache_dir": str(settings.assets.proxy_cache_dir),
}))
"""

# the core bundle, e.g. /_solara/cdn/@widgetti/solara-vuetify3-app@5.2.0/dist/solara-vuetify-app8.min.js
CORE_BUNDLE_RE = re.compile(r"/@widgetti/(solara-vuetify3?-app)@([^/]+)/dist/solara-vuetify-app\d(?:\.min)?\.js(?:\?|$)")
MSG_TYPE_RE = re.compile(rb'"msg_type":\s*"([a-z_]+)"')
METHOD_RE = re.compile(rb'"method":\s*"([a-z_-]+)"')
MAX_MESSAGES = 20


def parse_configs(spec: str) -> List[str]:
    if spec == "default":
        return list(DEFAULT_CONFIGS)
    if spec == "all":
        return list(ALL_CONFIGS)
    configs = [c.strip() for c in spec.split(",") if c.strip()]
    for config in configs:
        app, _, preset = config.partition("@")
        if app not in APPS or preset not in PRESETS:
            raise ValueError(f"Unknown config {config!r}, expected app@preset with app in {sorted(APPS)} and preset in {PRESETS}")
    return configs


def server_env(keep_env: bool) -> Tuple[Dict[str, str], List[str]]:
    """The environment for the servers and the probe, and the names of the variables removed."""
    env = dict(os.environ)
    stripped: List[str] = []
    if not keep_env:
        stripped = sorted(name for name in env if name.upper().startswith("SOLARA_"))
        for name in stripped:
            del env[name]
    env.pop("GITHUB_STEP_SUMMARY", None)
    env["SOLARA_TELEMETRY_MIXPANEL_ENABLE"] = "false"
    return env, stripped


def probe(python: str, env: Dict[str, str], cwd: str) -> Dict[str, Any]:
    """Versions and settings of the solara that the server will import, and whether it knows --frontend."""
    out = subprocess.run([python, "-c", PROBE_CODE], env=env, cwd=cwd, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"probe failed:\n{out.stderr}")
    info: Dict[str, Any] = json.loads(out.stdout.strip().splitlines()[-1])
    help_env = dict(env, COLUMNS="200")
    help_out = subprocess.run([python, "-m", "solara", "run", "--help"], env=help_env, cwd=cwd, capture_output=True, text=True, timeout=120)
    info["frontend_supported"] = "--frontend" in help_out.stdout
    return info


def git_sha() -> Optional[str]:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short=10", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return (sha + ("-dirty" if dirty else "")) or None


def loadavg() -> Optional[float]:
    try:
        return round(os.getloadavg()[0], 2)
    except (AttributeError, OSError):  # windows
        return None


def bundle_source(proxy_cache_dir: str, package: str, package_version: str) -> Tuple[str, str]:
    """('devlink' or 'cache/solara-assets', resolved path) for the dist directory the server serves."""
    dist = Path(proxy_cache_dir) / "@widgetti" / f"{package}@{package_version}" / "dist"
    real = Path(os.path.realpath(dist))
    packages = (REPO_ROOT / "packages").resolve()
    if real.parent.parent == packages and real.name == "dist":
        return "devlink", str(real)
    if real != dist and real.name == "dist" and real.parent.parent.name == "packages":
        return "devlink (other checkout)", str(real)
    return "cache/solara-assets", str(real)


class Server:
    def __init__(self, config: str, python: str, env: Dict[str, str], cwd: str, log_path: Path):
        app, _, preset = config.partition("@")
        self.config = config
        self.log_path = log_path
        self.port = get_free_port()
        self.url = f"http://localhost:{self.port}"
        app_path = HERE / "apps" / APPS[app][0]
        cmd = [
            python,
            "-m",
            "solara",
            "run",
            str(app_path),
            "--port",
            str(self.port),
            "--production",
            "--no-open",
            "--host",
            "localhost",
            "--log-level=warning",
        ]
        # full is the default: no flag, so the row measures what users get on master
        if preset != "full":
            cmd.append(f"--frontend={preset}")
        self.cmd = cmd
        self._log: IO[bytes] = open(log_path, "wb")
        self.proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=self._log, stderr=subprocess.STDOUT)

    def wait_ready(self, timeout: float = SERVER_START_TIMEOUT) -> Optional[str]:
        """None when /readyz answers, otherwise the reason."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            code = self.proc.poll()
            if code is not None:
                return f"server exited with code {code}, see {self.log_path}"
            try:
                with urllib.request.urlopen(self.url + "/readyz", timeout=2) as response:
                    if response.status == 200:
                        return None
            except OSError:
                pass
            time.sleep(0.1)
        return f"server not ready after {timeout:.0f} s, see {self.log_path}"

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(10)
        self._log.close()

    def log_text(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


class Network:
    """Collects the CDP network events of one page."""

    def __init__(self) -> None:
        self.requests: Dict[str, Dict[str, Any]] = {}
        self.ws_open: List[float] = []
        # (direction, timestamp, msg_type, method)
        self.frames: List[Tuple[str, float, Optional[str], Optional[str]]] = []
        self.last_activity = time.monotonic()

    def attach(self, cdp: CDPSession) -> None:
        cdp.on("Network.requestWillBeSent", self._will_be_sent)
        cdp.on("Network.dataReceived", self._data)
        cdp.on("Network.loadingFinished", self._finished)
        cdp.on("Network.loadingFailed", self._failed)
        cdp.on("Network.webSocketHandshakeResponseReceived", lambda p: self.ws_open.append(p["timestamp"]))
        cdp.on("Network.webSocketFrameReceived", lambda p: self._frame("recv", p))
        cdp.on("Network.webSocketFrameSent", lambda p: self._frame("sent", p))

    def _will_be_sent(self, p: Dict[str, Any]) -> None:
        self.last_activity = time.monotonic()
        request = self.requests.setdefault(p["requestId"], {"start": p["timestamp"], "raw": 0})
        request["url"] = p["request"]["url"]  # a redirect keeps the id, keep the first start

    def _data(self, p: Dict[str, Any]) -> None:
        request = self.requests.get(p["requestId"])
        if request is not None:
            request["raw"] += p["dataLength"]

    def _finished(self, p: Dict[str, Any]) -> None:
        self.last_activity = time.monotonic()
        request = self.requests.get(p["requestId"])
        if request is not None:
            request["end"] = p["timestamp"]
            request["transfer"] = p["encodedDataLength"]

    def _failed(self, p: Dict[str, Any]) -> None:
        self.last_activity = time.monotonic()
        request = self.requests.get(p["requestId"])
        if request is not None:
            request["end"] = p["timestamp"]
            request["failed"] = p.get("errorText")

    def _frame(self, direction: str, p: Dict[str, Any]) -> None:
        response = p["response"]
        data = response["payloadData"]
        payload = base64.b64decode(data) if response["opcode"] == 2 else data.encode()
        msg_type = MSG_TYPE_RE.search(payload)
        method = METHOD_RE.search(payload)
        self.frames.append((direction, p["timestamp"], msg_type.group(1).decode() if msg_type else None, method.group(1).decode() if method else None))

    def in_flight(self) -> bool:
        return any("end" not in r for r in self.requests.values())


class VisitData:
    """Everything one visit collected, next to the summary record."""

    def __init__(self, visit: Visit, network: Network, t0: float):
        self.visit = visit
        self.network = network
        self.t0 = t0


async def visit_page(context: BrowserContext, url: str, text: str, throttle: bool, label: str, settle_idle: bool = False) -> VisitData:
    page = await context.new_page()
    try:
        cdp = await context.new_cdp_session(page)
        network = Network()
        network.attach(cdp)
        errors: List[str] = []
        warnings: List[str] = []

        def on_console(message: ConsoleMessage) -> None:
            if message.type == "error":
                errors.append(message.text[:300])
            elif message.type == "warning":
                warnings.append(message.text[:300])

        page.on("console", on_console)
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"[:300]))
        await cdp.send("Network.enable")
        await cdp.send("Performance.enable", {"timeDomain": "timeTicks"})
        if throttle:
            await cdp.send(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": THROTTLE["latency_ms"],
                    "downloadThroughput": THROTTLE["down_mbit"] * 1_000_000 / 8,
                    "uploadThroughput": THROTTLE["up_mbit"] * 1_000_000 / 8,
                },
            )
            await cdp.send("Emulation.setCPUThrottlingRate", {"rate": THROTTLE["cpu"]})
        await page.add_init_script(INIT_JS % json.dumps(text))
        await page.goto(url, wait_until="commit", timeout=VISIT_TIMEOUT_MS)
        await page.wait_for_function("window.__fv !== undefined", timeout=VISIT_TIMEOUT_MS, polling=100)
        metrics = {m["name"]: m["value"] for m in (await cdp.send("Performance.getMetrics"))["metrics"]}
        fv: float = await page.evaluate("window.__fv")
        dcl: float = await page.evaluate("performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd")

        t0 = min(r["start"] for r in network.requests.values())

        def rel(timestamp: float) -> float:
            return round((timestamp - t0) * 1000, 1)

        before = [r for r in network.requests.values() if rel(r["start"]) <= fv]
        loop = asyncio.get_running_loop()
        if settle_idle:
            deadline = loop.time() + IDLE_CAP
            while loop.time() < deadline and (network.in_flight() or time.monotonic() - network.last_activity < IDLE_QUIET):
                await asyncio.sleep(0.05)
        else:
            deadline = loop.time() + SETTLE_CAP
            while loop.time() < deadline and any("end" not in r for r in before):
                await asyncio.sleep(0.05)
        await cdp.detach()

        def first_frame(direction: str, msg_type: Optional[str] = None, method: Optional[str] = None, after: float = 0) -> Optional[float]:
            for d, t, mt, me in network.frames:
                if d == direction and t >= after and (msg_type is None or mt == msg_type) and (method is None or me == method):
                    return t
            return None

        run_sent = first_frame("sent", method="run")
        finished = first_frame("recv", method="finished", after=run_sent) if run_sent is not None else None
        comm_open = first_frame("recv", msg_type="comm_open")
        visit: Visit = {
            "label": label,
            "first_widget": round(fv, 1),
            "dcl": round(dcl, 1),
            "ws_open": rel(min(network.ws_open)) if network.ws_open else None,
            "first_comm_open": rel(comm_open) if comm_open is not None else None,
            "session_start": round((finished - run_sent) * 1000, 1) if finished is not None and run_sent is not None else None,
            "script_ms": round(metrics.get("ScriptDuration", 0) * 1000, 1),
            "task_ms": round(metrics.get("TaskDuration", 0) * 1000, 1),
            "requests": len(before),
            "xfer_kb": round(sum(r.get("transfer") or 0 for r in before) / 1024, 1),
            "raw_kb": round(sum(r["raw"] for r in before) / 1024, 1),
            "errors": errors[:MAX_MESSAGES],
            "warnings": warnings[:MAX_MESSAGES],
        }
        return VisitData(visit, network, t0)
    finally:
        await page.close()


async def safe_visit(context: BrowserContext, url: str, text: str, throttle: bool, label: str) -> Visit:
    try:
        return (await visit_page(context, url, text, throttle, label)).visit
    except Exception as e:
        return {"label": label, "error": repr(e)[:500]}


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


async def warmup(pw: Playwright, server: Server, text: str) -> Tuple[Optional[VisitData], str]:
    """One discarded cold visit: fills the proxy cache and the server's first session cost."""
    reason = ""
    for attempt in range(WARMUP_ATTEMPTS):
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context(viewport=VIEWPORT)
            return await visit_page(context, server.url, text, False, "warmup", settle_idle=True), ""
        except Exception as e:
            reason = repr(e)[:500]
            log(f"{server.config}: warm-up attempt {attempt + 1} failed: {reason}")
        finally:
            await browser.close()
    return None, reason


async def measure_config(pw: Playwright, server: Server, runs: int, throttled_runs: int, meta: Dict[str, Any]) -> ConfigResult:
    app, _, preset = server.config.partition("@")
    text = APPS[app][1]
    result: ConfigResult = {"name": server.config, "app": app, "preset": preset, "server_log": str(server.log_path)}
    reason = server.wait_ready()
    warm_page: Optional[VisitData] = None
    if reason is None:
        warm_page, reason = await warmup(pw, server, text)
    if warm_page is None:
        result["failed"] = reason
        result["lazy"] = lazy_features([server.log_text()])
        return result
    warm_visit = warm_page.visit
    log(f"{server.config}: warm-up first widget {warm_visit['first_widget']:.0f} ms")
    result["idle_xfer_kb"] = round(sum(r.get("transfer") or 0 for r in warm_page.network.requests.values()) / 1024, 1)
    for request in warm_page.network.requests.values():
        match = CORE_BUNDLE_RE.search(request["url"])
        if match and "main_bundle_bytes" not in meta:
            meta["main_bundle_bytes"] = request["raw"]
            meta["main_bundle_url"] = re.sub(r"^https?://[^/]+", "", request["url"])
            meta["bundle_source"], meta["bundle_path"] = bundle_source(meta["proxy_cache_dir"], match.group(1), match.group(2))
            if not meta["bundle_source"].startswith("devlink"):
                log(f"warning: the frontend bundle does not come from this checkout's packages/*/dist ({meta['bundle_path']})")

    all_runs: Dict[str, ProfileRuns] = {}
    for profile, count in (("fast", runs), ("throttled", throttled_runs)):
        throttle = profile == "throttled"
        cold: List[Visit] = []
        warm: List[Visit] = []
        for i in range(count):
            browser: Browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context(viewport=VIEWPORT)
                cold.append(await safe_visit(context, server.url, text, throttle, f"{profile}-cold-{i}"))
                _log_visit(server.config, cold[-1])
                if not throttle or i == 0:
                    await asyncio.sleep(WARM_SLEEP)
                    warm.append(await safe_visit(context, server.url, text, throttle, f"{profile}-warm-{i}"))
                    _log_visit(server.config, warm[-1])
            finally:
                await browser.close()
        all_runs[profile] = {"cold": cold, "warm": warm}
    result["runs"] = all_runs
    result["median"] = {profile: {"cold": aggregate(r["cold"]), "warm": aggregate(r["warm"])} for profile, r in all_runs.items() if r["cold"]}
    messages = [server.log_text()] + warm_visit.get("warnings", [])
    for profile_runs in all_runs.values():
        for visit in profile_runs["cold"] + profile_runs["warm"]:
            messages += visit.get("warnings", [])
    result["lazy"] = lazy_features(messages)
    return result


def _log_visit(config: str, visit: Visit) -> None:
    if visit.get("error"):
        log(f"{config} {visit['label']}: failed: {visit['error']}")
    else:
        log(f"{config} {visit['label']}: first widget {visit['first_widget']:.0f} ms, {visit['requests']} requests, {visit['xfer_kb']:.0f} KB")


async def _run(
    configs: List[str], runs: int, throttled_runs: int, python: str, env: Dict[str, str], cwd: str, out: Path, meta: Dict[str, Any]
) -> List[ConfigResult]:
    servers: Dict[str, Server] = {}
    results: List[ConfigResult] = []
    try:
        for config in configs:
            preset = config.partition("@")[2]
            if preset != "full" and not meta["frontend_supported"]:
                continue
            servers[config] = Server(config, python, env, cwd, out.with_name(f"{out.stem}.server-{config.replace('@', '-')}.log"))
        async with async_playwright() as pw:
            for config in configs:
                server = servers.get(config)
                if server is None:
                    app, _, preset = config.partition("@")
                    log(f"{config}: skipped: preset not supported")
                    results.append({"name": config, "app": app, "preset": preset, "skipped": "preset not supported"})
                    continue
                if "chromium" not in meta:
                    browser = await pw.chromium.launch(headless=True)
                    meta["chromium"] = browser.version
                    await browser.close()
                results.append(await measure_config(pw, server, runs, throttled_runs, meta))
    finally:
        for server in servers.values():
            server.stop()
    return results


def default_out() -> Path:
    return Path(tempfile.gettempdir()) / "solara-bench" / (time.strftime("%Y%m%d-%H%M%S") + ".json")


def run_benchmark(
    configs: Sequence[str] = DEFAULT_CONFIGS,
    runs: int = 5,
    throttled_runs: int = 3,
    out: Optional[Path] = None,
    compare_path: Optional[Path] = None,
    keep_env: bool = False,
    python: str = sys.executable,
) -> BenchResult:
    """Run the benchmark, write JSON to out and markdown next to it (.md), print the markdown.

    Also appends the markdown to $GITHUB_STEP_SUMMARY when that is set.
    """
    configs = list(configs)
    for config in configs:
        parse_configs(config)  # validates
    out = default_out() if out is None else Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    env, stripped = server_env(keep_env)
    cwd = tempfile.mkdtemp(prefix="solara-bench-")
    try:
        info = probe(python, env, cwd)
        meta: Dict[str, Any] = dict(info)
        meta.update(
            git_sha=git_sha(),
            cpus=os.cpu_count(),
            loadavg_start=loadavg(),
            playwright=version("playwright"),
            runs={"fast": {"cold": runs, "warm": runs}, "throttled": {"cold": throttled_runs, "warm": min(throttled_runs, 1)}},
            throttle=THROTTLE,
            stripped_env=stripped,
        )
        if not info["frontend_supported"]:
            log("solara run has no --frontend option: the non-full presets are skipped")
        results = asyncio.run(_run(configs, runs, throttled_runs, python, env, cwd, out, meta))
    finally:
        shutil.rmtree(cwd, ignore_errors=True)
    meta["loadavg_end"] = loadavg()
    result: BenchResult = {"schema": 1, "meta": meta, "configs": results}
    out.write_text(json.dumps(result, indent=1))
    base: Optional[BenchResult] = json.loads(Path(compare_path).read_text()) if compare_path else None
    markdown = markdown_table(result, base)
    out.with_suffix(".md").write_text(markdown)
    print(markdown)
    write_step_summary(markdown)
    log(f"wrote {out} and {out.with_suffix('.md')}")
    return result


def main() -> None:
    @click.command(help=__doc__)
    @click.option("--configs", default="default", show_default=True, help="'default', 'all', or a comma separated list of app@preset.")
    @click.option("--runs", default=5, show_default=True, help="Cold visits (each followed by a warm one), unthrottled.")
    @click.option("--throttled-runs", default=3, show_default=True, help="Cold visits with throttling (a warm visit after the first only).")
    @click.option("--quick", is_flag=True, help="3 unthrottled runs and no throttling.")
    @click.option("--out", type=click.Path(path_type=Path), default=None, help="JSON output file (markdown goes next to it as .md).")
    @click.option("--compare", "compare_path", type=click.Path(exists=True, path_type=Path), default=None, help="Base JSON file, adds a Δ column.")
    @click.option("--keep-env", is_flag=True, help="Do not remove SOLARA_* variables from the server environment.")
    def command(configs: str, runs: int, throttled_runs: int, quick: bool, out: Optional[Path], compare_path: Optional[Path], keep_env: bool) -> None:
        if quick:
            runs, throttled_runs = 3, 0
        result = run_benchmark(parse_configs(configs), runs, throttled_runs, out, compare_path, keep_env)
        sys.exit(1 if any(c.get("failed") for c in result["configs"]) else 0)

    command()


if __name__ == "__main__":
    main()
