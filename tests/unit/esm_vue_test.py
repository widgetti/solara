from pathlib import Path

import pytest

ipyvue = pytest.importorskip("ipyvue")

if not hasattr(ipyvue, "define_module"):
    pytest.skip("requires ipyvue with ES module support (>=3.0.0a9)", allow_module_level=True)

from solara.server import esm_vue, kernel_context  # noqa: E402
from solara.server.kernel import Kernel  # noqa: E402


@pytest.fixture()
def clean_esm_state():
    modules = esm_vue._modules.copy()
    esm_vue._modules.clear()
    added = dict(esm_vue._modules_added_per_kernel)
    esm_vue._modules_added_per_kernel.clear()
    try:
        yield
    finally:
        esm_vue._modules.clear()
        esm_vue._modules.update(modules)
        esm_vue._modules_added_per_kernel.clear()
        esm_vue._modules_added_per_kernel.update(added)


@pytest.fixture()
def virtual_context(clean_esm_state):
    context = kernel_context.VirtualKernelContext(id="esm-vue-test-1", kernel=Kernel(), session_id="session-esm-vue-1")
    try:
        with context:
            yield context
    finally:
        context.close()


def test_create_modules_per_kernel_reuse(virtual_context):
    esm_vue.define_module("esm-vue-test-module", "export default 1")
    widgets = esm_vue.create_modules()
    widget = widgets["esm-vue-test-module"]
    # a second call must reuse the same (live) widget for this kernel
    assert esm_vue.create_modules()["esm-vue-test-module"] is widget


def test_create_modules_recreates_closed_widget(virtual_context):
    esm_vue.define_module("esm-vue-test-module", "export default 1")
    widget = esm_vue.create_modules()["esm-vue-test-module"]
    # context.restart() closes the kernel's widgets on (hot) reload; updating
    # a trait on a closed widget never reaches the browser, so create_modules
    # must hand out a fresh widget instead
    widget.close()
    assert widget.comm is None
    widget2 = esm_vue.create_modules()["esm-vue-test-module"]
    assert widget2 is not widget
    assert widget2.comm is not None


def test_redefine_module_updates_live_widget(virtual_context):
    esm_vue.define_module("esm-vue-test-module", "export default 1")
    widget = esm_vue.create_modules()["esm-vue-test-module"]
    esm_vue.define_module("esm-vue-test-module", "export default 2")
    assert esm_vue.create_modules()["esm-vue-test-module"] is widget
    assert widget.code == "export default 2"


def test_define_module_path_is_watched(clean_esm_state, tmp_path: Path, monkeypatch):
    from solara.server import reload

    watched = []
    monkeypatch.setattr(reload.reloader.watcher, "add_file", lambda file: watched.append(str(file)))
    module = tmp_path / "bundle.mjs"
    module.write_text("export default 1")
    esm_vue.define_module("esm-vue-test-path-module", module)
    assert watched == [str(module)]


def test_kernel_bookkeeping_dropped_on_close(clean_esm_state):
    context = kernel_context.VirtualKernelContext(id="esm-vue-test-2", kernel=Kernel(), session_id="session-esm-vue-2")
    with context:
        esm_vue.define_module("esm-vue-test-module", "export default 1")
        esm_vue.create_modules()
        assert "esm-vue-test-2" in esm_vue._modules_added_per_kernel
    context.close()
    assert "esm-vue-test-2" not in esm_vue._modules_added_per_kernel


def test_component_vue_esm_widget(virtual_context):
    import solara
    from solara.components.component_vue import _widget_vue

    @_widget_vue(None, esm_module="esm-vue-test-module", esm_export="Counter")
    def Counter(count: int = 0):
        pass

    widget = Counter(count=3)
    assert widget.template.esm_module == "esm-vue-test-module"
    assert widget.template.esm_export == "Counter"
    assert widget.count == 3

    # and via the public decorator (returns a reacton component)
    @solara.component_vue(esm_module="esm-vue-test-module", esm_export="Counter")
    def CounterComponent(count: int = 0):
        pass

    box, _rc = solara.render(CounterComponent(count=5), handle_error=False)
    widget = box.children[0]
    assert widget.template.esm_module == "esm-vue-test-module"
    assert widget.count == 5


def test_get_module_urls(clean_esm_state, tmp_path: Path):
    esm_vue.define_module("esm-vue-url-module", "/static/public/bundle.mjs")
    module = tmp_path / "bundle.mjs"
    module.write_text("export default 1")
    esm_vue.define_module("esm-vue-file-module", module)
    # only url-backed modules can be preloaded by the page
    assert esm_vue.get_module_urls() == ["/static/public/bundle.mjs"]
