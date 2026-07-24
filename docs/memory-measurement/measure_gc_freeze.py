"""Measure the gc-pause benefit of settings.main.gc_freeze on a 1-CPU docker container.

Runs gc_freeze_bench_app.py (big module-level baseline + per-kernel payload) twice -
SOLARA_GC_FREEZE=false and =true - in python:3.11-slim with --cpus 1. Each round opens
and closes N pages sequentially; every close triggers solara's kernel.gc_after_close
full collection. The app's gc callback prints GCSTAT lines; we parse them from the
container logs and report gen-2 pause statistics plus page open wall-clock times
(the user-visible cost of gc pauses on one cpu).
"""

import asyncio
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.request

from playwright.async_api import async_playwright

PORT = int(os.environ.get("MEASURE_PORT", "18796"))
BASE = f"http://localhost:{PORT}"
N_PAGES = int(os.environ.get("MEASURE_PAGES", "30"))
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
NAME = "solara-gc-freeze-bench"


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def wait_for_kernels(n, timeout=30.0):
    start = time.monotonic()
    while True:
        with urllib.request.urlopen(f"{BASE}/resourcez", timeout=10) as f:
            if json.loads(f.read())["kernels"]["total"] == n:
                return
        if time.monotonic() - start > timeout:
            raise TimeoutError(f"kernels != {n}")
        time.sleep(0.25)


async def run_round(freeze: bool):
    sh(["docker", "rm", "-f", NAME])
    run = sh(
        [
            "docker",
            "run",
            "-d",
            "--name",
            NAME,
            "--cpus",
            "1",
            "--memory",
            "2g",
            "-p",
            f"{PORT}:{PORT}",
            "-v",
            f"{REPO}:/repo:ro",
            "-v",
            f"{HERE}:/scratch:ro",
            "-e",
            "SOLARA_KERNEL_CULL_TIMEOUT=0.5s",
            "-e",
            f"SOLARA_GC_FREEZE={'true' if freeze else 'false'}",
            "python:3.11-slim",
            "bash",
            "-c",
            f"pip install -q /repo '/repo/packages/solara-server[starlette]' && "
            f"solara run /scratch/gc_freeze_bench_app.py --host 0.0.0.0 --port {PORT} --no-open --production --log-level info",
        ]
    )
    if run.returncode != 0:
        raise RuntimeError(run.stderr)
    for _ in range(360):
        try:
            urllib.request.urlopen(f"{BASE}/resourcez", timeout=5)
            break
        except Exception:
            time.sleep(1)
    else:
        print(sh(["docker", "logs", NAME]).stdout[-2000:])
        raise RuntimeError("server did not start")

    open_times = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for i in range(N_PAGES):
            t0 = time.perf_counter()
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(BASE, wait_until="networkidle")
            button = page.locator("button:has-text('Clicked')")
            await button.wait_for(timeout=30000)
            await button.click()
            await page.locator("button:has-text('Clicked: 1')").wait_for(timeout=10000)
            await page.locator("text=payload: 125000").wait_for(timeout=10000)
            open_times.append(time.perf_counter() - t0)
            await context.close()
            wait_for_kernels(0)
            time.sleep(1.5)  # let the deferred gc-after-close collection run
        await browser.close()

    logs = sh(["docker", "logs", NAME]).stdout + sh(["docker", "logs", NAME]).stderr
    sh(["docker", "rm", "-f", NAME])
    frozen = re.search(r"gc\.freeze: (\d+) startup objects", logs)
    gen2 = [float(m.group(1)) for m in re.finditer(r"GCSTAT gen=2 ms=([0-9.]+)", logs)]
    return {
        "freeze": freeze,
        "frozen_objects": int(frozen.group(1)) if frozen else 0,
        "gen2_collections": len(gen2),
        "gen2_ms_mean": round(statistics.mean(gen2), 1) if gen2 else None,
        "gen2_ms_median": round(statistics.median(gen2), 1) if gen2 else None,
        "gen2_ms_max": round(max(gen2), 1) if gen2 else None,
        "page_open_s_mean": round(statistics.mean(open_times), 2),
        "page_open_s_max": round(max(open_times), 2),
    }


async def main():
    results = []
    for freeze in [False, True]:
        print(f"=== SOLARA_GC_FREEZE={freeze} ===", flush=True)
        r = await run_round(freeze)
        results.append(r)
        print(json.dumps(r), flush=True)
    off, on = results
    if off["gen2_ms_mean"] and on["gen2_ms_mean"]:
        print(f"gen-2 pause mean: {off['gen2_ms_mean']} ms -> {on['gen2_ms_mean']} ms ({off['gen2_ms_mean'] / on['gen2_ms_mean']:.1f}x)", flush=True)
    with open(os.path.join(HERE, "report-gc-freeze.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
