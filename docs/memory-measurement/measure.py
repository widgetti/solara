"""Measure memory of a solara server serving a small test app.

Usage: python measure.py [app.py] [marker-text]

  app.py       app file in this directory (default: click_app.py)
  marker-text  optional text to wait for after the clicks, so apps can signal
               "every feature finished" (kitchen_sink_app.py renders ALL-DONE)

Starts `solara run <app> --production` as a subprocess, drives it with
real Chromium pages (playwright), and measures the server process RSS from the
outside with psutil. Per cycle:

  idle -> open N pages (each clicks the button 3x and verifies the render) ->
  measure loaded RSS -> close pages -> wait until /resourcez reports 0 kernels ->
  settle -> measure idle RSS again.

Repeats CYCLES times so we can tell allocator retention (plateau) from a leak
(linear growth). Prints a per-cycle table and a JSON blob at the end.
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

import psutil
from playwright.async_api import async_playwright

PORT = int(os.environ.get("MEASURE_PORT", "18765"))
BASE = f"http://localhost:{PORT}"
N_PAGES = 10
CYCLES = 10
CLICKS_PER_PAGE = int(os.environ.get("MEASURE_CLICKS", "3"))
HERE = os.path.dirname(os.path.abspath(__file__))
APP = sys.argv[1] if len(sys.argv) > 1 else "click_app.py"
MARKER = sys.argv[2] if len(sys.argv) > 2 else None


def phys_footprint(pid: int):
    """macOS: physical footprint via vmmap (what Activity Monitor shows).

    Includes compressed and swapped dirty pages, unlike RSS. Returns (current, peak)
    in bytes, or (None, None) off-macOS / on failure.
    """
    if sys.platform != "darwin":
        return None, None
    try:
        out = subprocess.run(["vmmap", "-summary", str(pid)], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return None, None
    cur = peak = None
    units = {"K": 1024, "M": 1024**2, "G": 1024**3}
    for line in out.splitlines():
        if line.startswith("Physical footprint:"):
            val = line.split(":")[1].strip()
            cur = float(val[:-1]) * units[val[-1]]
        elif line.startswith("Physical footprint (peak):"):
            val = line.split(":")[1].strip()
            peak = float(val[:-1]) * units[val[-1]]
    return cur, peak


def rss_of(proc: psutil.Process) -> int:
    total = proc.memory_info().rss
    for child in proc.children(recursive=True):
        try:
            total += child.memory_info().rss
        except psutil.Error:
            pass
    return total


def uss_of(proc: psutil.Process):
    try:
        return proc.memory_full_info().uss
    except psutil.Error:
        return None


def resourcez(verbose=False):
    url = f"{BASE}/resourcez" + ("?verbose=1" if verbose else "")
    with urllib.request.urlopen(url, timeout=10) as f:
        return json.loads(f.read())


def wait_for_kernels(n: int, timeout: float = 30.0) -> float:
    """Poll /resourcez until kernel count == n. Returns seconds waited."""
    start = time.monotonic()
    while True:
        data = resourcez()
        if data["kernels"]["total"] == n:
            return time.monotonic() - start
        if time.monotonic() - start > timeout:
            raise TimeoutError(f"kernels stuck at {data['kernels']['total']}, wanted {n}")
        time.sleep(0.25)


async def open_and_click(browser, results):
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(BASE, wait_until="networkidle")
    button = page.locator("button:has-text('Clicked')")
    await button.wait_for(timeout=30000)
    for i in range(CLICKS_PER_PAGE):
        await button.click()
        await page.locator(f"button:has-text('Clicked: {i + 1}')").wait_for(timeout=10000)
    if MARKER:
        await page.locator(f"text={MARKER}").wait_for(timeout=10000)
    results.append(context)


async def main():
    env = os.environ.copy()
    env["SOLARA_KERNEL_CULL_TIMEOUT"] = "0.5s"
    solara_bin = os.path.join(os.path.dirname(sys.executable), "solara")
    server = subprocess.Popen(
        [solara_bin, "run", os.path.join(HERE, APP), "--port", str(PORT), "--no-open", "--production"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    proc = psutil.Process(server.pid)
    report: dict = {"cycles": [], "platform": sys.platform}
    try:
        # wait for server up
        for _ in range(120):
            try:
                resourcez()
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("server did not start")

        report["rss_startup"] = rss_of(proc)

        async with async_playwright() as p:
            browser = await p.chromium.launch()

            # warmup: one full cycle so imports/JIT/caches are paid for
            contexts: list = []
            await open_and_click(browser, contexts)
            for c in contexts:
                await c.close()
            wait_for_kernels(0)
            time.sleep(2.0)
            report["rss_warm_baseline"] = rss_of(proc)
            report["uss_warm_baseline"] = uss_of(proc)

            for cycle in range(CYCLES):
                fp_idle_before, _ = phys_footprint(server.pid)
                rss_idle_before = rss_of(proc)
                contexts = []
                # sequential open: cleaner attribution, avoids load spikes
                for _ in range(N_PAGES):
                    await open_and_click(browser, contexts)
                r = resourcez()
                assert r["kernels"]["total"] == N_PAGES, r["kernels"]
                time.sleep(1.0)
                rss_loaded = rss_of(proc)
                fp_loaded, _ = phys_footprint(server.pid)
                ws_open = r["websockets"]["open"]
                threads_active = r["threads"]["active"]
                for c in contexts:
                    await c.close()
                cull_wait = wait_for_kernels(0)
                time.sleep(2.0)
                rss_idle_after = rss_of(proc)
                fp_idle_after, fp_peak = phys_footprint(server.pid)
                row = {
                    "cycle": cycle,
                    "rss_idle_before": rss_idle_before,
                    "rss_loaded": rss_loaded,
                    "rss_idle_after": rss_idle_after,
                    "fp_idle_before": fp_idle_before,
                    "fp_loaded": fp_loaded,
                    "fp_idle_after": fp_idle_after,
                    "fp_peak": fp_peak,
                    "per_kernel": (fp_loaded - fp_idle_before) / N_PAGES if fp_loaded else (rss_loaded - rss_idle_before) / N_PAGES,
                    "cull_wait_s": round(cull_wait, 2),
                    "ws_open": ws_open,
                    "threads_active": threads_active,
                    "kernels_after": resourcez()["kernels"]["total"],
                }
                report["cycles"].append(row)
                print(
                    f"cycle {cycle}: fp idle {fp_idle_before / 1e6:7.1f} MB -> loaded {fp_loaded / 1e6:7.1f} MB "
                    f"-> idle {fp_idle_after / 1e6:7.1f} MB (peak {fp_peak / 1e6:.1f}) | per-kernel {row['per_kernel'] / 1e6:5.2f} MB | "
                    f"rss {rss_idle_before / 1e6:.0f}/{rss_loaded / 1e6:.0f}/{rss_idle_after / 1e6:.0f} | "
                    f"threads {threads_active} | kernels after close: {row['kernels_after']}",
                    flush=True,
                )
            await browser.close()

        report["uss_final"] = uss_of(proc)
        report["resourcez_verbose"] = resourcez(verbose=True)
    finally:
        server.send_signal(signal.SIGINT)
        try:
            server.wait(10)
        except subprocess.TimeoutExpired:
            server.kill()

    report_name = f"report-{os.path.splitext(APP)[0]}.json"
    with open(os.path.join(HERE, report_name), "w") as f:
        json.dump(report, f, indent=2)
    print(f"wrote {report_name}")


if __name__ == "__main__":
    asyncio.run(main())
