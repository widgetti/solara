from pathlib import Path
from typing import TYPE_CHECKING, cast

import ipyvue
import ipywidgets as widgets
import traitlets
from reacton.core import _RenderContext

import solara
from solara.server import kernel_context

if TYPE_CHECKING:
    import playwright.sync_api

HERE = Path(__file__).parent


ipyvue.register_component_from_string(
    "external-split-widget",
    """
    <template>
      <Splitpanes class="external-split-widget" style="height: 160px; border: 2px solid #2563eb;">
        <Pane size="45">
          <div class="external-pane">External Vue library pane</div>
        </Pane>
        <Pane size="55">
          <div class="nested-widget-pane">
            <jupyter-widget :widget="widget"></jupyter-widget>
          </div>
        </Pane>
      </Splitpanes>
    </template>

    <script setup>
    import { Splitpanes, Pane } from "https://esm.sh/splitpanes@4.0.4?external=vue";
    </script>

    <style>
    @import url("https://unpkg.com/splitpanes@4.0.4/dist/splitpanes.css");

    .external-pane,
    .nested-widget-pane {
      box-sizing: border-box;
      height: 100%;
      padding: 12px;
    }

    .external-pane {
      background: #eff6ff;
      color: #1e3a8a;
      font-weight: 600;
    }
    </style>
    """,
)


ipyvue.register_component_from_string(
    "full-vue-only-widget",
    """
    <template>
      <section class="full-vue-only-widget">
        Full Vue component works
      </section>
    </template>

    <style>
    .full-vue-only-widget {
      border: 2px solid #16a34a;
      color: #14532d;
      font-weight: 600;
      padding: 12px;
    }
    </style>
    """,
)


class ExternalLibraryWidget(ipyvue.VueTemplate):
    template = """
    <template>
      <external-split-widget :widget="child"></external-split-widget>
    </template>
    """

    child = traitlets.Any().tag(sync=True, **widgets.widget_serialization)


class JupyterWidgetOnly(ipyvue.VueTemplate):
    template = """
    <template>
      <div class="jupyter-widget-only">
        <jupyter-widget :widget="child"></jupyter-widget>
      </div>
    </template>
    """

    child = traitlets.Any().tag(sync=True, **widgets.widget_serialization)


class FullVueOnlyWidget(ipyvue.VueTemplate):
    template = """
    <template>
      <full-vue-only-widget></full-vue-only-widget>
    </template>
    """


@solara.component
def ExternalWidgetApp():
    child = solara.use_memo(lambda: widgets.Button(description="Nested widget works"), [])
    return ExternalLibraryWidget.element(child=child)


@solara.component
def JupyterWidgetOnlyApp():
    child = solara.use_memo(lambda: widgets.Button(description="Plain jupyter-widget works"), [])
    return JupyterWidgetOnly.element(child=child)


@solara.component
def FullVueOnlyApp():
    return FullVueOnlyWidget.element()


external_widget_app = ExternalWidgetApp()
jupyter_widget_only_app = JupyterWidgetOnlyApp()
full_vue_only_app = FullVueOnlyApp()


def test_popout_external_library_jupyter_widget(page_session: "playwright.sync_api.Page", solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("popout_external_widget_test:ExternalWidgetApp"):
        page_session.goto(solara_server.base_url + "?solara-no-close-beacon")
        page_session.locator(".external-split-widget").wait_for()
        page_session.locator("text=Nested widget works").wait_for()

        contexts = list(kernel_context.contexts.values())
        assert len(contexts) == 1
        context = contexts[0]
        kernel_id = context.id
        rc = cast(_RenderContext, context.app_object)
        widget = rc.find(ExternalLibraryWidget).widget
        model_id = widget._model_id

        page_session.goto(solara_server.base_url + f"?kernelid={kernel_id}&modelid={model_id}")
        page_session.locator(".external-split-widget").wait_for()
        page_session.locator("text=External Vue library pane").wait_for()
        page_session.locator("text=Nested widget works").wait_for()


def test_popout_jupyter_widget_only(page_session: "playwright.sync_api.Page", solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("popout_external_widget_test:JupyterWidgetOnlyApp"):
        page_session.goto(solara_server.base_url + "?solara-no-close-beacon")
        page_session.locator(".jupyter-widget-only").wait_for()
        page_session.locator("text=Plain jupyter-widget works").wait_for()

        contexts = list(kernel_context.contexts.values())
        assert len(contexts) == 1
        context = contexts[0]
        kernel_id = context.id
        rc = cast(_RenderContext, context.app_object)
        widget = rc.find(JupyterWidgetOnly).widget
        model_id = widget._model_id

        page_session.goto(solara_server.base_url + f"?kernelid={kernel_id}&modelid={model_id}")
        page_session.locator(".jupyter-widget-only").wait_for()
        page_session.locator("text=Plain jupyter-widget works").wait_for()


def test_popout_full_vue_only(page_session: "playwright.sync_api.Page", solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("popout_external_widget_test:FullVueOnlyApp"):
        page_session.goto(solara_server.base_url + "?solara-no-close-beacon")
        page_session.locator(".full-vue-only-widget").wait_for()
        page_session.locator("text=Full Vue component works").wait_for()

        contexts = list(kernel_context.contexts.values())
        assert len(contexts) == 1
        context = contexts[0]
        kernel_id = context.id
        rc = cast(_RenderContext, context.app_object)
        widget = rc.find(FullVueOnlyWidget).widget
        model_id = widget._model_id

        page_session.goto(solara_server.base_url + f"?kernelid={kernel_id}&modelid={model_id}")
        page_session.locator(".full-vue-only-widget").wait_for()
        page_session.locator("text=Full Vue component works").wait_for()
