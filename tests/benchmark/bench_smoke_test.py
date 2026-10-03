import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_one_cold_run_writes_json(tmp_path: Path):
    # one cold visit of the smallest app; needs network on the first run, to fill the proxy cache
    out = tmp_path / "bench.json"
    # keep the run out of the CI job summary
    env = {name: value for name, value in os.environ.items() if name != "GITHUB_STEP_SUMMARY"}
    cmd = [sys.executable, "-m", "tests.benchmark.bench", "--configs", "hello@full", "--runs", "1", "--throttled-runs", "0", "--out", str(out)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=110)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-4000:]
    result = json.loads(out.read_text())
    assert result["schema"] == 1
    (config,) = result["configs"]
    assert config["name"] == "hello@full"
    assert not config.get("failed")
    (cold,) = config["runs"]["fast"]["cold"]
    assert not cold.get("error"), cold
    assert cold["first_widget"] > 0
    assert cold["requests"] > 0
    assert cold["session_start"] is not None
    assert "hello@full" in out.with_suffix(".md").read_text()
