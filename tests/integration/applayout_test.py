import time
from pathlib import Path

import playwright.sync_api

import solara

HERE = Path(__file__).parent


@solara.component
def Page():
    with solara.Sidebar():
        solara.Text("sidebar text")
    with solara.AppBarTitle():
        solara.Text("app bar title")
    solara.Text("main content")


def _layout(page: playwright.sync_api.Page):
    drawer = page.locator(".v-navigation-drawer").bounding_box()
    assert drawer is not None
    result = {"drawer_right": drawer["x"] + drawer["width"]}
    for name, text in [("title", "app bar title"), ("content", "main content")]:
        box = page.locator(f"text={text}").bounding_box()
        assert box is not None
        # the element at the left edge of the text, to see if the drawer covers it
        under_drawer = page.evaluate(
            "([x, y]) => !!document.elementFromPoint(x, y)?.closest('.v-navigation-drawer')",
            [box["x"] + 2, box["y"] + box["height"] / 2],
        )
        result[name] = {"x": box["x"], "under_drawer": under_drawer}
    return result


def _wait_for_layout(page: playwright.sync_api.Page, check, timeout=10):
    # Vuetify positions the app bar and the main content after the drawer registers
    start = time.time()
    layout = _layout(page)
    while not check(layout) and time.time() - start < timeout:
        page.wait_for_timeout(100)
        layout = _layout(page)
    return layout


def test_applayout_sidebar_next_to_content(page_session: playwright.sync_api.Page, solara_app, extra_include_path, solara_server):
    # On Vue 3, a drawer width that is not a number made the drawer cover the app bar and the main content
    viewport = page_session.viewport_size
    # wide enough that both Vue 2 and Vue 3 show the drawer next to the content, not as an overlay
    page_session.set_viewport_size({"width": 1440, "height": 900})
    try:
        with extra_include_path(HERE), solara_app("applayout_test"):
            page_session.goto(solara_server.base_url + "/")
            page_session.locator("text=sidebar text").wait_for()
            page_session.locator("text=main content").wait_for()

            def open_ok(layout):
                return not layout["title"]["under_drawer"] and not layout["content"]["under_drawer"] and layout["content"]["x"] >= layout["drawer_right"]

            layout = _wait_for_layout(page_session, open_ok)
            assert layout["drawer_right"] > 0
            assert open_ok(layout), layout

            # the menu icon must not be under the drawer, and closing the sidebar gives the content the full width
            page_session.locator(".v-app-bar-nav-icon, .v-app-bar__nav-icon").click()

            def closed_ok(layout):
                return layout["drawer_right"] <= 0 and layout["content"]["x"] < 100

            layout = _wait_for_layout(page_session, closed_ok)
            assert closed_ok(layout), layout
    finally:
        if viewport is not None:
            page_session.set_viewport_size(viewport)
