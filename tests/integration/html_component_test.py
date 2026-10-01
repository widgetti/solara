import uuid

from playwright.sync_api import Page, expect
from starlette.applications import Starlette
from starlette.routing import Mount

import solara.server.starlette
from solara.server import settings


def test_html_component_bindings_controller_and_python_child(tmp_path, page_session: Page, solara_server, solara_app, extra_include_path):
    app_name = "html_component_app_" + uuid.uuid4().hex[:8]
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    public = tmp_path / "public"
    public.mkdir()
    (public / "shared.css").write_text(".native-counter { color: rgb(12, 34, 56); }", encoding="utf-8")
    (public / "shared.js").write_text("export function mark(host) { host.dataset.shared = 'loaded'; }", encoding="utf-8")
    (app_dir / "counter.html").write_text(
        """<template>
  <div class="native-counter">
    <output data-solara-text="name" data-solara-attr-title="name"></output>
    <input data-solara-model="name">
    <button data-solara-event-click="reset">Reset</button>
    <button class="controller-reset">Controller reset</button>
    <slot></slot>
  </div>
</template>
<style>@import '../public/shared.css'; :host { display: block; }</style>
<script type="module">
  import {mark} from '../public/shared.js';
  export function mount({root, set, subscribe, emit}) {
    root.host.dataset.controller = "mounted";
    mark(root.host);
    const input = root.querySelector('input');
    const reset = root.querySelector('.controller-reset');
    const onKeydown = event => { if (event.key === 'Escape') set('name', 'Controller'); };
    const onReset = () => emit('reset', null);
    const unsubscribe = subscribe('name', value => { root.host.dataset.observed = value; });
    input.addEventListener('keydown', onKeydown);
    reset.addEventListener('click', onReset);
    return () => {
      root.host.dataset.controller = "disposed";
      input.removeEventListener('keydown', onKeydown);
      reset.removeEventListener('click', onReset);
      unsubscribe();
    };
  }
</script>
""",
        encoding="utf-8",
    )
    (app_dir / "native_button.html").write_text(
        """<template><button data-solara-text="label" data-solara-event-click="click"></button></template>
<style>:host { display: inline-block; } button { color: rgb(25, 50, 75); }</style>""",
        encoding="utf-8",
    )
    (app_dir / (app_name + ".py")).write_text(
        """import solara

@solara.component_html("counter.html")
def Counter(name="World", on_name=None, event_reset=None, children=[]):
    pass

@solara.component_html("native_button.html")
def NativeButton(label="Native child", event_click=None):
    pass

@solara.component
def Page():
    first, set_first = solara.use_state("World")
    second, set_second = solara.use_state("Other")
    show, set_show = solara.use_state(True)
    if show:
        Counter(name=first, on_name=set_first, event_reset=lambda _data: set_first("Reset"),
                children=[NativeButton(event_click=lambda _data: set_first("Native")), solara.Button("Python child")])
        Counter(name=second, on_name=set_second, children=[])
    solara.Button("Remove counters", on_click=lambda: set_show(False))
""",
        encoding="utf-8",
    )

    with extra_include_path(app_dir), solara_app(app_name + ":Page"):
        page_session.goto(solara_server.base_url)
        host = page_session.locator(".solara-html-component").filter(has=page_session.locator(".native-counter"))
        expect(host).to_have_count(2)
        first = host.nth(0)
        second = host.nth(1)
        expect(first.locator("output")).to_have_text("World")
        expect(second.locator("output")).to_have_text("Other")
        expect(first).to_have_attribute("data-controller", "mounted")
        expect(first).to_have_attribute("data-shared", "loaded")
        expect(first.locator(".native-counter")).to_have_css("color", "rgb(12, 34, 56)")
        expect(first.get_by_text("Python child")).to_be_visible()
        expect(first.get_by_role("button", name="Native child")).to_be_visible()
        first.get_by_role("button", name="Native child").click()
        expect(first.locator("output")).to_have_text("Native")
        expect(first.get_by_role("button", name="Native child")).to_be_focused()

        first.locator("input").fill("Ada")
        expect(first.locator("output")).to_have_text("Ada")
        expect(first.locator("output")).to_have_attribute("title", "Ada")
        expect(first).to_have_attribute("data-observed", "Ada")
        expect(first.locator("input")).to_be_focused()
        expect(second.locator("output")).to_have_text("Other")
        first.locator("input").press("Escape")
        expect(first.locator("output")).to_have_text("Controller")
        first.get_by_role("button", name="Controller reset").click()
        expect(first.locator("input")).to_have_value("Reset")

        first_element = first.element_handle()
        page_session.get_by_role("button", name="Remove counters").click()
        expect(host).to_have_count(0)
        assert first_element.evaluate("element => element.dataset.controller") == "disposed"


def test_html_component_draft_commits_on_pause_enter_or_blur(tmp_path, page_session: Page, solara_server, solara_app, extra_include_path):
    app_name = "html_component_draft_" + uuid.uuid4().hex[:8]
    (tmp_path / "draft.html").write_text(
        """<template>
  <input type="text">
  <button type="button">Leave field</button>
  <output data-solara-text="commits"></output>
</template>
<script type="module">
export function mount({root, get, set, subscribe}) {
  const input = root.querySelector('input');
  let timer;
  input.value = get('value');
  const commit = () => { clearTimeout(timer); set('value', input.value); };
  const onInput = () => { clearTimeout(timer); timer = setTimeout(commit, 400); };
  const onFocus = () => { root.host.dataset.focused = 'yes'; };
  const onBlur = () => { root.host.dataset.focused = 'no'; commit(); };
  const onKeydown = event => {
    if (event.key === 'Enter') commit();
    if (event.key === 'Escape') { clearTimeout(timer); input.value = get('value'); }
  };
  input.addEventListener('input', onInput);
  input.addEventListener('focus', onFocus);
  input.addEventListener('blur', onBlur);
  input.addEventListener('keydown', onKeydown);
  const stop = subscribe('value', value => { input.value = value; });
  return () => {
    clearTimeout(timer);
    input.removeEventListener('input', onInput);
    input.removeEventListener('focus', onFocus);
    input.removeEventListener('blur', onBlur);
    input.removeEventListener('keydown', onKeydown);
    stop();
  };
}
</script>""",
        encoding="utf-8",
    )
    (tmp_path / (app_name + ".py")).write_text(
        """import solara
@solara.component_html("draft.html")
def Draft(value="start", on_value=None, commits=0):
    pass
@solara.component
def Page():
    value, set_value = solara.use_state("start")
    commits, set_commits = solara.use_state(0)
    def commit(new_value):
        set_value(new_value)
        set_commits(commits + 1)
    Draft(value=value, on_value=commit, commits=commits)
""",
        encoding="utf-8",
    )

    with extra_include_path(tmp_path), solara_app(app_name + ":Page"):
        page_session.goto(solara_server.base_url)
        host = page_session.locator(".solara-html-component")
        input = host.locator("input")
        commits = host.locator("output")
        expect(input).to_have_value("start")
        expect(commits).to_have_text("0")

        input.fill("first")
        expect(host).to_have_attribute("data-focused", "yes")
        expect(commits).to_have_text("0")  # Browser-only draft before the timer fires.
        expect(commits).to_have_text("1", timeout=3000)

        input.fill("second")
        input.press("Enter")
        expect(commits).to_have_text("2")
        input.fill("discarded")
        input.press("Escape")
        expect(input).to_have_value("second")
        expect(commits).to_have_text("2")

        input.fill("third")
        host.get_by_role("button", name="Leave field").click()
        expect(host).to_have_attribute("data-focused", "no")
        expect(commits).to_have_text("3")


def test_html_component_public_assets_under_root_path(tmp_path, page_session: Page, solara_app, extra_include_path):
    app_name = "html_component_mount_" + uuid.uuid4().hex[:8]
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    public = tmp_path / "public"
    public.mkdir()
    (public / "shared.css").write_text(".mounted { color: rgb(21, 43, 65); }", encoding="utf-8")
    (public / "shared.js").write_text("export const answer = 'shared';", encoding="utf-8")
    (app_dir / "greeting.html").write_text(
        """<template><span class="mounted">Mounted</span><a href="../public/shared.js">Asset</a></template>
<style>@import '../public/shared.css';</style>
<script type="module">
import {answer} from '../public/shared.js';
export function mount({root}) { root.host.dataset.answer = answer; }
</script>""",
        encoding="utf-8",
    )
    (app_dir / (app_name + ".py")).write_text(
        """import solara
@solara.component_html("greeting.html")
def Greeting():
    pass
@solara.component
def Page():
    Greeting()
""",
        encoding="utf-8",
    )

    settings.main.root_path = None
    settings.main.base_url = ""
    server = None
    try:
        mounted_app = Starlette(routes=[Mount("/solara_mount/", routes=solara.server.starlette.routes)])
        server = solara.server.starlette.ServerStarlette(port=0, starlette_app=mounted_app)
        server.serve_threaded()
        server.wait_until_serving()
        with extra_include_path(app_dir), solara_app(app_name + ":Page", init=False):
            page_session.goto(server.base_url + "/solara_mount/")
            host = page_session.locator(".solara-html-component")
            expect(host).to_have_attribute("data-answer", "shared")
            expect(host.locator(".mounted")).to_have_css("color", "rgb(21, 43, 65)")
            expect(host.locator("a")).to_have_attribute("href", server.base_url + "/solara_mount/static/public/shared.js")
    finally:
        page_session.goto("about:blank")
        if server is not None:
            server.stop_serving()
        settings.main.root_path = None
        settings.main.base_url = ""


def test_html_component_removed_during_module_import(tmp_path, page_session: Page, solara_server, solara_app, extra_include_path):
    app_name = "html_component_slow_" + uuid.uuid4().hex[:8]
    (tmp_path / "slow.html").write_text(
        """<template><p>Slow component</p></template>
<script type="module">
await new Promise(resolve => setTimeout(resolve, 1200));
export function mount({root}) { root.host.dataset.lateMount = "yes"; }
</script>""",
        encoding="utf-8",
    )
    (tmp_path / (app_name + ".py")).write_text(
        """import solara
@solara.component_html("slow.html")
def Slow():
    pass
@solara.component
def Page():
    show, set_show = solara.use_state(True)
    if show:
        Slow()
    solara.Button("Remove slow", on_click=lambda: set_show(False))
""",
        encoding="utf-8",
    )

    with extra_include_path(tmp_path), solara_app(app_name + ":Page"):
        page_session.goto(solara_server.base_url)
        host = page_session.locator(".solara-html-component")
        expect(host).to_have_count(1)
        element = host.element_handle()
        page_session.get_by_role("button", name="Remove slow").click()
        expect(host).to_have_count(0)
        page_session.wait_for_timeout(1400)
        assert element.evaluate("node => node.dataset.lateMount || null") is None
