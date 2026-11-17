import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from solara.checks import getcmdline


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process lookup")
def test_windows_process_executable():
    assert Path(getcmdline(os.getpid())).samefile(getattr(sys, "_base_executable", sys.executable))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process lookup")
def test_windows_process_executable_with_spaces_and_unicode(tmp_path):
    executable = tmp_path / "process with spaces and \u00fcnicode.exe"
    shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe", executable)
    with subprocess.Popen(
        [str(executable), "/d", "/q"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    ) as process:
        try:
            assert Path(getcmdline(process.pid)).samefile(executable)
        finally:
            process.communicate(b"exit\r\n", timeout=10)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process lookup")
def test_windows_process_lookup_error():
    with pytest.raises(OSError):
        getcmdline(0)
