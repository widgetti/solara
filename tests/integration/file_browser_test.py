from pathlib import Path

import playwright.sync_api
import pytest

import solara


@pytest.mark.parametrize("multiple", [False, True])
def test_file_browser_selection_events(solara_test, page_session: playwright.sync_api.Page, tmp_path: Path, multiple: bool):
    (tmp_path / "first.txt").write_text("first")
    (tmp_path / "second.txt").write_text("second")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("nested")

    @solara.component
    def Page():
        selection = solara.use_reactive("none")
        opened = solara.use_reactive("none")

        if multiple:
            solara.FileBrowserMultiple(
                tmp_path,
                on_paths_select=lambda paths: selection.set(",".join(path.name for path in paths) or "none"),
                on_file_open=lambda path: opened.set(path.name),
            )
        else:
            solara.FileBrowser(
                tmp_path,
                can_select=True,
                on_path_select=lambda path: selection.set(Path(path).name if path is not None else "none"),
                on_file_open=lambda path: opened.set(path.name),
            )
        solara.Text(selection.value, classes=["selected-paths"])
        solara.Text(opened.value, classes=["opened-path"])

    solara.display(Page())
    first = page_session.locator(".solara-file-list-file").filter(has_text="first.txt")
    second = page_session.locator(".solara-file-list-file").filter(has_text="second.txt")
    selection = page_session.locator(".selected-paths")
    first.click()
    playwright.sync_api.expect(selection).to_have_text("first.txt")
    second.click()
    playwright.sync_api.expect(selection).to_have_text("first.txt,second.txt" if multiple else "second.txt")

    if multiple:
        first.click()
        playwright.sync_api.expect(selection).to_have_text("second.txt")
        playwright.sync_api.expect(page_session.locator(".solara-file-list-selected")).to_have_count(1)
        first.click()
        playwright.sync_api.expect(selection).to_have_text("second.txt,first.txt")

    first.dblclick()
    playwright.sync_api.expect(page_session.locator(".opened-path")).to_have_text("first.txt")
    playwright.sync_api.expect(selection).to_have_text("none")
    page_session.locator(".solara-file-list-dir").filter(has_text="subdir").dblclick()
    playwright.sync_api.expect(page_session.locator(".solara-file-list-file")).to_have_text("nested.txt - 6 Bytes")


def test_file_browser_open_events(solara_test, page_session: playwright.sync_api.Page, tmp_path: Path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("nested")

    @solara.component
    def Page():
        opened = solara.use_reactive("none")
        solara.FileBrowser(tmp_path, on_file_open=lambda path: opened.set(path.name))
        solara.Text(opened.value, classes=["opened-path"])

    solara.display(Page())
    page_session.locator(".solara-file-list-dir").filter(has_text="subdir").click()
    page_session.locator(".solara-file-list-file").filter(has_text="nested.txt").click()
    playwright.sync_api.expect(page_session.locator(".opened-path")).to_have_text("nested.txt")
