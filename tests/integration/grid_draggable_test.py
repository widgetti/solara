import playwright.sync_api
import pytest
from playwright.sync_api import expect

from .conftest import SERVERS


# GridDraggable loads its grid library from the CDN at runtime, and needs a
# different library for Vue 2 and Vue 3. With the Vue 2 library under Vue 3,
# the grid stayed empty (https://github.com/widgetti/solara/issues/1268).
def test_grid_draggable(ipywidgets_runner, page_session: playwright.sync_api.Page, request):
    if request.node.callspec.params["ipywidgets_runner"] != "solara" and request.node.callspec.params["solara_server"] != SERVERS[0]:
        pytest.skip("No need to run this test for all servers.")

    # this function (or rather its lines) will be executed in the kernel
    # voila, lab, classic notebook and solara will all execute it
    def kernel_code():
        from IPython.display import display

        import solara

        layout = solara.reactive([{"i": 0, "x": 0, "y": 0, "w": 4, "h": 4}, {"i": 1, "x": 4, "y": 0, "w": 4, "h": 4}])

        @solara.component
        def Page():
            with solara.Column():
                solara.Text(f"item 0 at x={layout.value[0]['x']}", classes=["test-grid-state"])
                solara.GridDraggable(
                    items=[solara.Text("grid item 0", classes=["test-grid-item-0"]), solara.Text("grid item 1", classes=["test-grid-item-1"])],
                    grid_layout=layout.value,
                    on_grid_layout=layout.set,
                )

        display(Page())

    ipywidgets_runner(kernel_code)
    item0 = page_session.locator(".test-grid-item-0")
    item1 = page_session.locator(".test-grid-item-1")
    # the grid library comes from the CDN, which can be slow on CI
    expect(item0).to_be_visible(timeout=60_000)
    expect(item1).to_be_visible()
    # in lab and notebook the output can be below the fold, and the drag uses viewport coordinates
    item0.scroll_into_view_if_needed()
    # the grid places the items next to each other, not below each other.
    # It first lays out at a default width, and then moves the items (with a
    # css transition) once it knows its own width, so wait for that.
    page_session.wait_for_function(
        """() => {
            const a = document.querySelector('.test-grid-item-0').getBoundingClientRect();
            const b = document.querySelector('.test-grid-item-1').getBoundingClientRect();
            return b.left > a.right && Math.abs(a.top - b.top) < 1;
        }"""
    )
    page_session.wait_for_timeout(500)  # let the css transition finish
    box0 = item0.bounding_box()
    box1 = item1.bounding_box()
    assert box0 is not None and box1 is not None

    # drag item 0 to the far right, the new layout must reach Python.
    # The grid has 12 columns and the item is 4 wide, so it ends at x=8.
    viewport = page_session.viewport_size
    assert viewport is not None
    page_session.mouse.move(box0["x"] + 5, box0["y"] + 5)
    page_session.mouse.down()
    page_session.mouse.move(viewport["width"] - 10, box0["y"] + 5, steps=10)
    page_session.mouse.up()
    expect(page_session.locator(".test-grid-state")).to_have_text("item 0 at x=8")
