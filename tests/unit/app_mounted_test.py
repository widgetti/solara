import sys
import textwrap

import solara
import solara.lab
import solara.server.app
from solara.server import kernel
from solara.server.app import AppScript, solara_comm_target
from solara.server.kernel_context import VirtualKernelContext


class _FakeComm:
    """The comm interface solara_comm_target needs: on_msg registration + send capture."""

    def __init__(self):
        self.sent: list = []
        self._handler = None

    def on_msg(self, handler):
        self._handler = handler

    def send(self, data):
        self.sent.append(data)

    def dispatch(self, data):
        assert self._handler is not None
        self._handler({"content": {"data": data}})


APP = """
import solara
import solara.lab
import mounted_recorder

@solara.component
def Page():
    mounted = solara.lab.app_mounted.value
    finished_sent = any(m.get("method") == "finished" for m in mounted_recorder.comm.sent)
    mounted_recorder.renders.append((mounted, finished_sent))
    return solara.Text("data" if mounted else "skeleton")
"""


def _run_app(tmpdir, extra_include_path, monkeypatch, context, dispatch_after=()):
    (tmpdir / "mounted_recorder.py").write_text("renders = []\ncomm = None\n", "utf8")
    (tmpdir / "mounted_app.py").write_text(textwrap.dedent(APP), "utf8")
    with extra_include_path(str(tmpdir)):
        import mounted_recorder

        fake = _FakeComm()
        mounted_recorder.comm = fake
        app = AppScript(str(tmpdir / "mounted_app.py"))
        app.init()
        monkeypatch.setitem(solara.server.app.apps, "__default__", app)
        try:
            with context:
                solara_comm_target(fake, None)
                fake.dispatch({"method": "run", "args": {"path": ""}})
                for message in dispatch_after:
                    fake.dispatch(message)
            return fake, list(mounted_recorder.renders)
        finally:
            app.close()
            sys.modules.pop("mounted_recorder", None)


def _new_context(name):
    return VirtualKernelContext(id=name, kernel=kernel.Kernel(), session_id=f"session-{name}")


def test_app_mounted_flips_after_finished(tmpdir, extra_include_path, monkeypatch, no_kernel_context):
    context = _new_context("mounted-run")
    try:
        fake, renders = _run_app(tmpdir, extra_include_path, monkeypatch, context)
        # every render before "finished" saw False, so the loader drops on the skeleton
        assert renders[0] == (False, False)
        assert all(not mounted for mounted, finished_sent in renders if not finished_sent)
        # and the set after "finished" rendered the data pass
        assert renders[-1] == (True, True)
        assert [m["method"] for m in fake.sent].count("finished") == 1
        with context:
            assert solara.lab.app_mounted.value is True
    finally:
        with context:
            context.close()


def test_app_mounted_is_per_kernel(tmpdir, extra_include_path, monkeypatch, no_kernel_context):
    mounted_context = _new_context("mounted-a")
    other_context = _new_context("mounted-b")
    try:
        _run_app(tmpdir, extra_include_path, monkeypatch, mounted_context)
        with mounted_context:
            assert solara.lab.app_mounted.value is True
        with other_context:
            # a kernel whose page did not mount yet still waits
            assert solara.lab.app_mounted.value is False
    finally:
        for context in (mounted_context, other_context):
            with context:
                context.close()


def test_app_mounted_after_reload(tmpdir, extra_include_path, monkeypatch, no_kernel_context):
    context = _new_context("mounted-reload")
    try:
        fake, renders = _run_app(tmpdir, extra_include_path, monkeypatch, context, dispatch_after=[{"method": "reload", "path": ""}])
        assert [m["method"] for m in fake.sent].count("finished") == 2
        assert renders[-1] == (True, True)
        with context:
            assert solara.lab.app_mounted.value is True
    finally:
        with context:
            context.close()


def test_app_mounted_false_without_server(kernel_context):
    # a kernel the server did not run (solara.render in a test): nothing sets it
    seen = []

    @solara.component
    def Page():
        seen.append(solara.lab.app_mounted.value)
        return solara.Text("x")

    box, rc = solara.render(Page(), handle_error=False)
    assert seen == [False]
    solara.lab.app_mounted.set(True)
    assert seen == [False, True]
    rc.close()


def test_app_mounted_true_outside_kernel(no_kernel_context):
    # a notebook or plain Python: the global scope, where the app shows at once
    assert solara.lab.app_mounted.value is True
