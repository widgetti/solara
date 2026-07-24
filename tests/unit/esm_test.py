from pathlib import Path

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
