import threading
from pathlib import Path
from typing import List, cast

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


def test_file_browser_multiple_modifiers(solara_test, page_session: playwright.sync_api.Page, tmp_path: Path):
    for name in ["a.txt", "b.txt", "c.txt", "d.txt", "z.txt"]:
        (tmp_path / name).write_text(name)

    @solara.component
    def Page():
        selection = solara.use_reactive("none")
        solara.FileBrowserMultiple(
            tmp_path,
            on_paths_select=lambda paths: selection.set(",".join(path.name for path in paths) or "none"),
        )
        solara.Text(selection.value, classes=["selected-paths"])

    solara.display(Page())
    files = page_session.locator(".solara-file-list-file")
    selection = page_session.locator(".selected-paths")
    files.filter(has_text="z.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("z.txt")
    files.filter(has_text="b.txt").click()
    files.filter(has_text="d.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("z.txt,b.txt,c.txt,d.txt")
    playwright.sync_api.expect(page_session.locator(".solara-file-list-selected .solara-file-list-file")).to_have_text(
        ["b.txt - 5 Bytes", "c.txt - 5 Bytes", "d.txt - 5 Bytes", "z.txt - 5 Bytes"]
    )

    # Resize and reverse the range while retaining the selection from before Shift.
    files.filter(has_text="c.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("z.txt,b.txt,c.txt")
    files.filter(has_text="a.txt").click(modifiers=["Shift", "ControlOrMeta"])
    playwright.sync_api.expect(selection).to_have_text("z.txt,b.txt,a.txt")
    files.filter(has_text="a.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("z.txt,b.txt,a.txt")

    files.filter(has_text="c.txt").click(modifiers=["ControlOrMeta"])
    playwright.sync_api.expect(selection).to_have_text("z.txt,b.txt,a.txt,c.txt")
    files.filter(has_text="c.txt").click(modifiers=["ControlOrMeta"])
    playwright.sync_api.expect(selection).to_have_text("z.txt,b.txt,a.txt")


def test_file_browser_range_highlights_before_callback(solara_test, page_session: playwright.sync_api.Page, tmp_path: Path):
    for name in ["a.txt", "b.txt", "c.txt", "d.txt"]:
        (tmp_path / name).write_text(name)
    block = threading.Event()
    entered = threading.Event()
    release = threading.Event()

    @solara.component
    def Page():
        selection = solara.use_reactive("none")

        def on_select(paths):
            if block.is_set():
                entered.set()
                assert release.wait(10)
            selection.set(",".join(path.name for path in paths) or "none")

        solara.FileBrowserMultiple(tmp_path, on_paths_select=on_select)
        solara.Text(selection.value, classes=["selected-paths"])

    solara.display(Page())
    files = page_session.locator(".solara-file-list-file")
    selection = page_session.locator(".selected-paths")
    highlighted = page_session.locator(".solara-file-list-selected .solara-file-list-file")
    files.filter(has_text="a.txt").click()
    playwright.sync_api.expect(selection).to_have_text("a.txt")
    block.set()
    try:
        files.filter(has_text="d.txt").click(modifiers=["Shift"])
        assert entered.wait(2)
        playwright.sync_api.expect(highlighted).to_have_text(["a.txt - 5 Bytes", "b.txt - 5 Bytes", "c.txt - 5 Bytes", "d.txt - 5 Bytes"])
        files.filter(has_text="b.txt").click(modifiers=["Shift"])
        playwright.sync_api.expect(highlighted).to_have_text(["a.txt - 5 Bytes", "b.txt - 5 Bytes"])
        files.filter(has_text="d.txt").click(modifiers=["Shift"])
        playwright.sync_api.expect(highlighted).to_have_text(["a.txt - 5 Bytes", "b.txt - 5 Bytes", "c.txt - 5 Bytes", "d.txt - 5 Bytes"])
        playwright.sync_api.expect(selection).to_have_text("a.txt")
    finally:
        release.set()
    playwright.sync_api.expect(selection).to_have_text("a.txt,b.txt,c.txt,d.txt")
    files.filter(has_text="c.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("a.txt,b.txt,c.txt")
    playwright.sync_api.expect(highlighted).to_have_text(["a.txt - 5 Bytes", "b.txt - 5 Bytes", "c.txt - 5 Bytes"])


def test_file_browser_range_anchor_resets(solara_test, page_session: playwright.sync_api.Page, tmp_path: Path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    for directory in [tmp_path, subdir]:
        for name in ["a.txt", "b.txt", "c.txt"]:
            (directory / name).write_text(name)

    @solara.component
    def Page():
        location = solara.use_reactive(tmp_path)
        selected = solara.use_reactive(cast(List[Path], []))
        solara.FileBrowserMultiple(location, selected=selected)
        solara.Button("Clear selection", on_click=lambda: selected.set([]))
        solara.Button("Change directory", on_click=lambda: location.set(subdir))
        solara.Text(",".join(str(path.relative_to(tmp_path)) for path in selected.value) or "none", classes=["selected-paths"])

    solara.display(Page())
    files = page_session.locator(".solara-file-list-file")
    selection = page_session.locator(".selected-paths")
    files.filter(has_text="a.txt").click()
    files.filter(has_text="c.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("a.txt,b.txt,c.txt")
    page_session.get_by_role("button", name="Clear selection", exact=True).click()
    playwright.sync_api.expect(selection).to_have_text("none")
    files.filter(has_text="c.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("c.txt")
    page_session.get_by_role("button", name="Change directory", exact=True).click()
    playwright.sync_api.expect(page_session.locator(".solara-file-browser")).to_contain_text(str(subdir))
    files.filter(has_text="a.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text("c.txt," + str(Path("subdir") / "a.txt"))
    files.filter(has_text="a.txt").dblclick()
    playwright.sync_api.expect(selection).to_have_text("none")
    files.filter(has_text="c.txt").click(modifiers=["Shift"])
    playwright.sync_api.expect(selection).to_have_text(str(Path("subdir") / "c.txt"))
