import time
from pathlib import Path

import playwright.sync_api

from playwright.sync_api import expect

import solara

HERE = Path(__file__).parent


@solara.component
def Page():
    with solara.Sidebar():
        solara.Text("sidebar text")
        # wider than the 400 px drawer on Vue 3
        solara.Div(style={"width": "500px", "height": "20px"}, classes=["wide-sidebar-element"])
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

            # sidebar content wider than the drawer must stay reachable: Vue 2 grows the drawer, Vue 3 scrolls it
            wide = page_session.locator(".wide-sidebar-element")

            def wide_right():
                box = wide.bounding_box()
                assert box is not None
                return box["x"] + box["width"]

            if wide_right() > layout["drawer_right"]:
                box = wide.bounding_box()
                assert box is not None
                page_session.mouse.move(box["x"] + 100, box["y"] + box["height"] / 2)
                page_session.mouse.wheel(300, 0)
                start = time.time()
                while wide_right() > layout["drawer_right"] and time.time() - start < 5:
                    page_session.wait_for_timeout(100)
            assert wide_right() <= layout["drawer_right"], (wide_right(), layout)

            # the menu icon must not be under the drawer, and closing the sidebar gives the content the full width
            nav_icon = page_session.locator(".v-app-bar-nav-icon, .v-app-bar__nav-icon")
            expect(nav_icon.locator(".mdi-menu")).to_be_visible()
            nav_icon.click()

            def closed_ok(layout):
                return layout["drawer_right"] <= 0 and layout["content"]["x"] < 100

            layout = _wait_for_layout(page_session, closed_ok)
            assert closed_ok(layout), layout
    finally:
        if viewport is not None:
            page_session.set_viewport_size(viewport)


def test_embedded_sidebar(ipywidgets_runner, page_session: playwright.sync_api.Page):
    def kernel_code():
        from IPython.display import display

        import solara
        from solara.components.applayout import _AppLayoutEmbed

        count = solara.reactive(0)

        @solara.component
        def Content():
            with solara.AppBarTitle():
                solara.Text("Embedded title")
            with solara.Sidebar():
                solara.Button("Increment from sidebar", on_click=lambda: count.set(count.value + 1))
            solara.Text(f"Count: {count.value}", classes=["embedded-sidebar-count"])

        # Exercise the notebook layout even when using the Solara server runner.
        display(_AppLayoutEmbed(children=[Content()]))

    ipywidgets_runner(kernel_code)
    expect(page_session.get_by_text("Embedded title", exact=True)).to_be_visible()
    count = page_session.locator(".embedded-sidebar-count")
    expect(count).to_have_text("Count: 0")
    activator = page_session.locator(".v-toolbar .v-app-bar-nav-icon, .v-toolbar .v-app-bar__nav-icon")
    sidebar_button = page_session.get_by_text("Increment from sidebar", exact=True)
    expect(sidebar_button).to_be_hidden()
    activator.click()
    expect(sidebar_button).to_be_visible()
    sidebar_button.click()
    expect(count).to_have_text("Count: 1")
    # Model controls must remain usable after a Python-side rerender.
    expect(sidebar_button).to_be_visible()
    sidebar_button.click()
    expect(count).to_have_text("Count: 2")
    count.click()
    expect(sidebar_button).to_be_hidden()
    activator.click()
    expect(sidebar_button).to_be_visible()
    expect(count).to_have_text("Count: 2")

    count.click()
    page_session.locator("button:has(.mdi-fullscreen)").click()
    exit_button = page_session.locator("button:has(.mdi-fullscreen-exit)")
    expect(exit_button).to_be_visible()
    expect(count).to_have_text("Count: 2")
    sidebar_button.click()
    expect(count).to_have_text("Count: 3")
    exit_button.click()
    expect(page_session.locator("button:has(.mdi-fullscreen)")).to_be_visible()
    expect(count).to_have_text("Count: 3")
    activator.click()
    expect(sidebar_button).to_be_visible()
