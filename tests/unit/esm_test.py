import threading
from pathlib import Path
from typing import List

import pytest

ipyreact = pytest.importorskip("ipyreact")

from solara.server import esm, kernel_context  # noqa: E402
from solara.server.kernel import Kernel  # noqa: E402


@pytest.fixture()
def clean_esm_state():
    modules = esm._modules.copy()
    esm._modules.clear()
    added = dict(esm._modules_added_per_kernel)
    esm._modules_added_per_kernel.clear()
    import_maps = dict(esm._import_map_per_kernel)
    esm._import_map_per_kernel.clear()
    try:
        yield
    finally:
        esm._modules.clear()
        esm._modules.update(modules)
        esm._modules_added_per_kernel.clear()
        esm._modules_added_per_kernel.update(added)
        esm._import_map_per_kernel.clear()
        esm._import_map_per_kernel.update(import_maps)


@pytest.fixture()
def virtual_context(clean_esm_state):
    context = kernel_context.VirtualKernelContext(id="esm-test-1", kernel=Kernel(), session_id="session-esm-1")
    try:
        with context:
            yield context
    finally:
        context.close()


def test_create_modules_per_kernel_reuse(virtual_context):
    esm.define_module("esm-test-module", code="export default 1")
    widgets = esm.create_modules()
    widget = widgets["esm-test-module"]
    # a second call must reuse the same (live) widget for this kernel
    assert esm.create_modules()["esm-test-module"] is widget


def test_create_modules_recreates_closed_widget(virtual_context):
    esm.define_module("esm-test-module", code="export default 1")
    widget = esm.create_modules()["esm-test-module"]
    # context.restart() closes the kernel's widgets on (hot) reload; updating
    # a trait on a closed widget never reaches the browser, so create_modules
    # must hand out a fresh widget instead
    widget.close()
    assert widget.comm is None
    widget2 = esm.create_modules()["esm-test-module"]
    assert widget2 is not widget
    assert widget2.comm is not None


def test_redefine_module_updates_live_widget(virtual_context):
    esm.define_module("esm-test-module", code="export default 1")
    widget = esm.create_modules()["esm-test-module"]
    esm.define_module("esm-test-module", code="export default 2")
    assert esm.create_modules()["esm-test-module"] is widget
    assert widget.code == "export default 2"


def _load_a_page():
    # Creating a module or import map widget sends a message. With starlette that send waits for
    # the event loop, and the event loop calls get_module_urls for every page request. If widget
    # creation held the lock that get_module_urls takes, the two would wait for each other forever.
    page = threading.Thread(target=esm.get_module_urls, daemon=True)
    page.start()
    page.join(5)
    assert not page.is_alive(), "get_module_urls waited for a thread that creates widgets"


def test_a_page_request_does_not_wait_for_module_creation(virtual_context, monkeypatch):
    read = esm._read
    reads = []

    def read_while_a_page_loads(module):
        _load_a_page()
        reads.append(module)
        return read(module)

    monkeypatch.setattr(esm, "_read", read_while_a_page_loads)
    esm.define_module("esm-test-module", code="export default 1")
    assert len(reads) == 1


def test_a_page_request_does_not_wait_for_the_import_map(virtual_context, monkeypatch):
    ImportMap = ipyreact.importmap.ImportMap

    def import_map_while_a_page_loads(**kwargs):
        _load_a_page()
        return ImportMap(**kwargs)

    monkeypatch.setattr(ipyreact.importmap, "ImportMap", import_map_while_a_page_loads)
    esm.create_import_map()
    assert isinstance(esm._import_map_per_kernel["esm-test-1"], ImportMap)


def test_a_hot_reload_waits_for_a_thread_that_still_applies_older_modules(virtual_context, monkeypatch):
    # context.restart (hot reload) drops the kernel's bookkeeping. A thread that still applies an
    # older copy of the modules must finish first, or the browser would get the older code last.
    esm.define_module("esm-test-module", code="export default 1")
    reading, resume = threading.Event(), threading.Event()
    read = esm._read
    published: List[str] = []

    def slow_read(module):
        if threading.current_thread() is slow:
            reading.set()
            assert resume.wait(5)
        published.append(read(module))
        return published[-1]

    monkeypatch.setattr(esm, "_read", slow_read)
    slow = threading.Thread(target=esm.create_modules, daemon=True)
    reload = threading.Thread(target=lambda: esm.define_module("esm-test-module", code="export default 2"), daemon=True)
    slow.start()
    try:
        assert reading.wait(5)
        virtual_context.restart()
        reload.start()
        reload.join(0.5)
        assert reload.is_alive(), "the reload did not wait for the slow thread"
    finally:
        resume.set()
        slow.join(5)
        if reload.ident is not None:
            reload.join(5)
    assert not slow.is_alive() and not reload.is_alive()
    assert published == ["export default 1", "export default 2"]


def test_define_module_path_is_watched(clean_esm_state, tmp_path: Path, monkeypatch):
    from solara.server import reload

    watched = []
    monkeypatch.setattr(reload.reloader.watcher, "add_file", lambda file: watched.append(str(file)))
    module = tmp_path / "bundle.mjs"
    module.write_text("export default 1")
    esm.define_module("esm-test-path-module", module)
    assert watched == [str(module)]


def test_kernel_bookkeeping_dropped_on_close(clean_esm_state):
    context = kernel_context.VirtualKernelContext(id="esm-test-2", kernel=Kernel(), session_id="session-esm-2")
    with context:
        esm.define_module("esm-test-module", code="export default 1")
        esm.create_modules()
        esm.create_import_map()
        assert "esm-test-2" in esm._modules_added_per_kernel
        assert "esm-test-2" in esm._import_map_per_kernel
    context.close()
    assert "esm-test-2" not in esm._modules_added_per_kernel
    assert "esm-test-2" not in esm._import_map_per_kernel
    assert "esm-test-2" not in esm._lock_per_kernel
