"""Ground-truth memory measurement: solara server in a memory-limited docker container.

The server (this worktree's code) runs in python:3.11-slim with --memory 512m
--memory-swap 512m. The browser (playwright chromium) runs on the host, so the
cgroup numbers are the server and nothing else. Per cycle we read:

  /sys/fs/cgroup/memory.current  - bytes charged right now (incl. page cache)
  /sys/fs/cgroup/memory.peak     - high-water mark
  memory.stat: anon              - anonymous (heap) pages: closest to "what the app needs"

Same cycle protocol as measure.py: open N pages, click, close, wait for kernel
cull via /resourcez, settle, measure.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request

from playwright.async_api import async_playwright

PORT = 18766
BASE = f"http://localhost:{PORT}"
N_PAGES = 10
CYCLES = 10
CLICKS_PER_PAGE = 3
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))  # the solara repo root
NAME = "solara-mem"
APP = sys.argv[1] if len(sys.argv) > 1 else "click_app.py"
MARKER = sys.argv[2] if len(sys.argv) > 2 else None


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def cgroup_mem():
    out = sh(
        ["docker", "exec", NAME, "sh", "-c", "cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak; grep '^anon ' /sys/fs/cgroup/memory.stat"]
    ).stdout.split()
    return {"current": int(out[0]), "peak": int(out[1]), "anon": int(out[3])}


def resourcez(verbose=False):
    url = f"{BASE}/resourcez" + ("?verbose=1" if verbose else "")
    with urllib.request.urlopen(url, timeout=10) as f:
        return json.loads(f.read())


def wait_for_kernels(n: int, timeout: float = 30.0) -> float:
    start = time.monotonic()
    while True:
        if resourcez()["kernels"]["total"] == n:
            return time.monotonic() - start
        if time.monotonic() - start > timeout:
            raise TimeoutError(f"kernels != {n}")
        time.sleep(0.25)


async def open_and_click(browser, contexts):
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
    contexts.append(context)


async def main():
    sh(["docker", "rm", "-f", NAME])
    run = sh(
        [
            "docker",
            "run",
            "-d",
            "--name",
            NAME,
            "--memory",
            "512m",
            "--memory-swap",
            "512m",
            "-p",
            f"{PORT}:{PORT}",
            "-v",
            f"{REPO}:/repo:ro",
            "-v",
            f"{HERE}:/scratch:ro",
            "-e",
            "SOLARA_KERNEL_CULL_TIMEOUT=0.5s",
            "-e",
            f"SOLARA_KERNEL_GC_AFTER_CLOSE={os.environ.get('SOLARA_KERNEL_GC_AFTER_CLOSE', 'true')}",
            "python:3.11-slim",
            "bash",
            "-c",
            f"pip install -q /repo '/repo/packages/solara-server[starlette]' && solara run /scratch/{APP} --host 0.0.0.0 --port {PORT} --no-open --production",
        ]
    )
    if run.returncode != 0:
        raise RuntimeError(run.stderr)
    print("container starting, installing solara...", flush=True)
    report: dict = {"cycles": []}
    try:
        for _ in range(360):  # pip install takes a while
            try:
                resourcez()
                break
            except Exception:
                time.sleep(1)
        else:
            print(sh(["docker", "logs", NAME]).stdout[-3000:])
            raise RuntimeError("server did not start")
        print("server up", flush=True)
        report["mem_startup"] = cgroup_mem()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            # warmup cycle
            contexts: list = []
            await open_and_click(browser, contexts)
            for c in contexts:
                await c.close()
            wait_for_kernels(0)
            time.sleep(2)
            report["mem_warm_baseline"] = cgroup_mem()

            for cycle in range(CYCLES):
                m_before = cgroup_mem()
                contexts = []
                for _ in range(N_PAGES):
                    await open_and_click(browser, contexts)
                r = resourcez()
                assert r["kernels"]["total"] == N_PAGES, r["kernels"]
                time.sleep(1)
                m_loaded = cgroup_mem()
                for c in contexts:
                    await c.close()
                cull_wait = wait_for_kernels(0)
                time.sleep(2)
                m_after = cgroup_mem()
                row = {
                    "cycle": cycle,
                    "before": m_before,
                    "loaded": m_loaded,
                    "after": m_after,
                    "per_kernel_anon": (m_loaded["anon"] - m_before["anon"]) / N_PAGES,
                    "cull_wait_s": round(cull_wait, 2),
                    "threads": r["threads"]["active"],
                    "kernels_after": resourcez()["kernels"]["total"],
                }
                report["cycles"].append(row)
                print(
                    f"cycle {cycle}: anon {m_before['anon'] / 1e6:6.1f} -> {m_loaded['anon'] / 1e6:6.1f} -> {m_after['anon'] / 1e6:6.1f} MB "
                    f"| current {m_after['current'] / 1e6:6.1f} MB | peak {m_after['peak'] / 1e6:6.1f} MB "
                    f"| per-kernel {row['per_kernel_anon'] / 1e6:5.2f} MB | threads {row['threads']} | kernels after: {row['kernels_after']}",
                    flush=True,
                )
            await browser.close()
        report["resourcez_final"] = resourcez(verbose=True)
        report["mem_final"] = cgroup_mem()
    finally:
        sh(["docker", "rm", "-f", NAME])

    report_name = f"report_docker-{os.path.splitext(APP)[0]}.json"
    with open(os.path.join(HERE, report_name), "w") as f:
        json.dump(report, f, indent=2)
    print(f"wrote {report_name}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
