import asyncio
import platform
import unittest.mock
from pathlib import Path
from typing import Optional, cast

import pytest

import solara
import solara.components.file_browser

HERE = Path(__file__)


def test_file_browser_callback_no_select():
    on_directory_change = unittest.mock.MagicMock()
    on_file_open = unittest.mock.MagicMock()
    on_file_name = unittest.mock.MagicMock()  # backwards compat test
    on_path_select = unittest.mock.MagicMock()

    @solara.component
    def Test():
        return solara.FileBrowser(
            HERE.parent, on_path_select=on_path_select, on_directory_change=on_directory_change, on_file_open=on_file_open, on_file_name=on_file_name
        )

    div, rc = solara.render_fixed(Test(), handle_error=False)
    on_directory_change.assert_not_called()
    on_file_open.assert_not_called()
    on_path_select.assert_not_called()

    list: solara.components.file_browser.FileListWidget = div.children[1]
    with pytest.raises(NameError, match=".*foo.*"):
        list.test_click("foo")
    # select ..
    list.test_click("..")
    on_directory_change.assert_called_once()
    on_file_open.assert_not_called()
    on_path_select.assert_not_called()
    assert "conftest.py" in list

    # select conftest.py
    list.test_click("conftest.py")
    conftest_path = Path(HERE).parent.parent / "conftest.py"
    on_file_open.assert_called_with(conftest_path)
    on_file_name.assert_called_with(str(conftest_path))
    on_path_select.assert_not_called()
    assert list.clicked is not None
    assert list.clicked["name"] == "conftest.py"

    list.clicked = None  # type: ignore
    on_file_open.assert_called_once()
    on_path_select.assert_not_called()

    list.test_click("unit")
    assert list.clicked is None


def test_file_browser_callback_can_select():
    on_directory_change = unittest.mock.MagicMock()
    on_file_open = unittest.mock.MagicMock()
    on_path_select = unittest.mock.MagicMock()

    @solara.component
    def Test():
        return solara.FileBrowser(
            HERE.parent, on_path_select=on_path_select, on_directory_change=on_directory_change, on_file_open=on_file_open, can_select=True
        )

    div, rc = solara.render_fixed(Test())
    on_directory_change.assert_not_called()
    on_file_open.assert_not_called()
    on_path_select.assert_not_called()

    list: solara.components.file_browser.FileListWidget = div.children[1]
    assert "file_browser_test.py" in list

    # select ..
    list.test_click("..")
    on_directory_change.assert_not_called()
    on_file_open.assert_not_called()
    on_path_select.assert_called_with(HERE.parent.parent)

    # change to ..
    list.test_click("..", double_click=True)
    on_directory_change.assert_called_once()
    on_file_open.assert_not_called()
    on_path_select.assert_called_with(None)
    assert "conftest.py" in list

    list.test_click("conftest.py")
    conftest_path = Path(HERE).parent.parent / "conftest.py"
    on_path_select.assert_called_with(conftest_path)

    # enter the current directory again
    list.test_click("unit", double_click=True)
    # we shouldn't have a file with the same name selected any more
    on_path_select.assert_called_with(None)
    assert list.double_clicked is None

    # open conftest
    list.test_click("conftest.py", double_click=True)
    conftest_path = Path(HERE).parent / "conftest.py"
    on_file_open.assert_called_with(conftest_path)

    list.clicked = None
    on_path_select.assert_called_with(None)

    # go up
    list.test_click("..", double_click=True)
    assert "conftest.py" in list

    # go up again
    list.test_click("..", double_click=True)
    assert "conftest.py" not in list


def test_file_browser_scroll_pos():
    @solara.component
    def Test():
        return solara.FileBrowser(HERE.parent)

    div, rc = solara.render_fixed(Test())

    list: solara.components.file_browser.FileListWidget = div.children[1]
    assert "file_browser_test.py" in list

    # select ..
    list.test_click("..")
    assert "unit" in list
    list.scroll_pos = 10

    # go to unit
    list.test_click("unit")

    # and back to ..
    list.test_click("..")
    assert list.scroll_pos == 10


@pytest.mark.skipif(platform.system() == "Windows", reason="Windows doesn't support chmod")
def test_file_browser_no_access(tmpdir: Path):
    on_directory_change = unittest.mock.MagicMock()
    on_file_open = unittest.mock.MagicMock()
    on_path_select = unittest.mock.MagicMock()

    path_no_read = tmpdir / "no_read"
    path_no_read.mkdir()
    mode = path_no_read.stat().mode  # type: ignore
    path_no_read.chmod(000)

    @solara.component
    def Test():
        return solara.FileBrowser(
            Path(tmpdir), on_path_select=on_path_select, on_directory_change=on_directory_change, on_file_open=on_file_open, can_select=True
        )

    try:
        div, rc = solara.render_fixed(Test(), handle_error=False)

        list: solara.components.file_browser.FileListWidget = div.children[1]
        # select is ok
        list.test_click("no_read")

        # enter is not
        on_path_select.assert_called_with(path_no_read)
        list.test_click("no_read", double_click=True)
        on_directory_change.assert_not_called()
    finally:
        path_no_read.chmod(mode)


def test_file_browser_filter():
    def directory_filter(path: Path) -> bool:
        return path.is_dir() and not path.name.startswith("_")

    @solara.component
    def Test():
        return solara.FileBrowser(HERE.parent.parent, filter=directory_filter)

    div, rc = solara.render_fixed(Test())

    list: solara.components.file_browser.FileListWidget = div.children[1]
    items = list.files
    names = {k["name"] for k in items}
    assert names.issuperset({"unit", "ui", "docs", "integration", "pyinstaller", ".."})


def test_file_browser_test_change_directory():
    div, rc = solara.render_fixed(solara.FileBrowser(HERE.parent))
    list: solara.components.file_browser.FileListWidget = div.children[1]
    assert "file_browser_test.py" in list
    rc.render(solara.FileBrowser(HERE.parent.parent))
    assert "file_browser_test.py" not in list


def test_file_browser_control_directory():
    import solara

    def directory_filter(path: Path) -> bool:
        return path.is_dir() and not path.name.startswith("_")

    BASE_PATH = HERE.parent.parent

    @solara.component
    def Page():
        def set_directory(path: Path) -> None:
            directory.value = path if str(path).startswith(str(BASE_PATH)) else BASE_PATH

        directory = solara.use_reactive(BASE_PATH, set_directory)
        solara.FileBrowser(directory, filter=directory_filter)

    _, rc = solara.render(Page(), handle_error=False)
    file_list = rc.find(solara.components.file_browser.FileListWidget).widget
    mock = unittest.mock.MagicMock()
    file_list.observe(mock, "files")
    items = file_list.files
    names = {k["name"] for k in items}
    assert names.issuperset({"unit", "ui", "docs", "integration", "pyinstaller", ".."})
    file_list.test_click("..")
    assert mock.call_count == 0
    file_list.test_click("integration")
    items = file_list.files
    names = {k["name"] for k in items}
    assert names != {"unit", "ui", "docs", "integration", "pyinstaller", ".."}
    assert mock.call_count == 1


def test_file_browser_relative_path():
    @solara.component
    def Test():
        return solara.FileBrowser(".")

    div, rc = solara.render_fixed(Test())
    list: solara.components.file_browser.FileListWidget = div.children[1]
    files = {k["name"] for k in list.files}
    list.test_click("..")
    files_parent = {k["name"] for k in list.files}
    assert files_parent != files


def test_file_browser_programmatic_select():
    # using a reactive value to select a file
    selected = solara.reactive(cast(Optional[Path], None))
    current_dir = solara.reactive(HERE.parent)

    @solara.component
    def Test():
        return solara.FileBrowser(HERE.parent, selected=selected, can_select=True)

    div, rc = solara.render_fixed(Test(), handle_error=False)
    list: solara.components.file_browser.FileListWidget = div.children[1]
    files = list.files.copy()
    assert list.clicked is None
    selected.value = HERE.parent / "file_browser_test.py"
    assert list.clicked is not None
    assert list.clicked["name"] == "file_browser_test.py"
    list.test_click("..", double_click=True)
    assert list.files != files
    assert selected.value is None

    selected.value = None
    rc.close()

    # passing selected as a value (non reactive)
    @solara.component
    def Test2():
        return solara.FileBrowser(HERE.parent, selected=selected.value, on_path_select=selected.set, can_select=True)

    div, rc = solara.render_fixed(Test2(), handle_error=False)
    list = div.children[1]
    files = list.files.copy()
    assert list.clicked is None
    selected.value = HERE.parent / "file_browser_test.py"
    assert list.clicked is not None
    assert list.clicked["name"] == "file_browser_test.py"
    list.test_click("..", double_click=True)
    assert list.files != files
    assert selected.value is None
    rc.close()

    @solara.component
    def Test3():
        return solara.FileBrowser(current_dir, selected=selected.value, on_path_select=selected.set, can_select=True)

    div, rc = solara.render_fixed(Test3(), handle_error=False)
    assert current_dir.value == HERE.parent
    list.test_click("..", double_click=False)
    assert current_dir.value == HERE.parent
    # this will trigger the sync_directory_from_selected
    selected.value = current_dir.value / ".." / "unit" / ".."
    assert current_dir.value == HERE.parent
    rc.close()


def test_file_browser_watch_no_event_loop(tmpdir: Path):
    """Test that watch=True gracefully handles no running event loop."""
    tmpdir = Path(tmpdir)
    (tmpdir / "test.txt").write_text("test")

    # When watch=True but no event loop is available, it should log a warning but not crash
    with unittest.mock.patch.object(solara.components.file_browser.logger, "warning") as mock_warning:

        @solara.component
        def Test():
            return solara.FileBrowser(tmpdir, watch=True)

        div, rc = solara.render_fixed(Test(), handle_error=False)
        file_list: solara.components.file_browser.FileListWidget = div.children[1]

        # Verify files are still shown correctly
        files = {k["name"] for k in file_list.files}
        assert "test.txt" in files

        # Verify warning was logged about no event loop
        mock_warning.assert_called_with("No running event loop, cannot watch directory for changes")
        rc.close()


def test_file_browser_watch_disabled_by_default():
    """Test that watch is disabled by default (no warning when watchfiles not available)."""

    @solara.component
    def Test():
        return solara.FileBrowser(HERE.parent)

    # This should work without any issues even if watchfiles is not installed
    div, rc = solara.render_fixed(Test(), handle_error=False)
    file_list: solara.components.file_browser.FileListWidget = div.children[1]
    assert "file_browser_test.py" in file_list
    rc.close()


def test_file_browser_watch_no_watchfiles(tmpdir: Path):
    """Test that watch=True logs a warning when watchfiles is not installed."""
    tmpdir = Path(tmpdir)
    (tmpdir / "test.txt").write_text("test")

    with unittest.mock.patch.object(solara.components.file_browser, "watchfiles", None):
        with unittest.mock.patch.object(solara.components.file_browser.logger, "warning") as mock_warning:

            @solara.component
            def Test():
                return solara.FileBrowser(tmpdir, watch=True)

            div, rc = solara.render_fixed(Test(), handle_error=False)

            # Give the effect a chance to run
            import time

            time.sleep(0.1)

            mock_warning.assert_called_with("watchfiles not installed, cannot watch directory")
            rc.close()


@pytest.mark.asyncio
async def test_file_browser_watch_detects_new_file(tmpdir: Path):
    """Test that watch=True actually detects when a new file is added."""
    tmpdir = Path(tmpdir)
    (tmpdir / "initial.txt").write_text("initial")

    files_changed_event = asyncio.Event()

    @solara.component
    def Test():
        return solara.FileBrowser(tmpdir, watch=True)

    div, rc = solara.render_fixed(Test(), handle_error=False)
    file_list: solara.components.file_browser.FileListWidget = div.children[1]

    # Verify initial state
    initial_files = {k["name"] for k in file_list.files}
    assert "initial.txt" in initial_files
    assert "new_file.txt" not in initial_files

    # Set up observer to detect when files trait changes
    def on_files_change(change):
        files_changed_event.set()

    file_list.observe(on_files_change, "files")

    # Give the watcher task a moment to start
    await asyncio.sleep(0.1)

    # Create a new file - this should trigger the watcher
    (tmpdir / "new_file.txt").write_text("new content")

    # Wait for the watcher to detect the change
    try:
        await asyncio.wait_for(files_changed_event.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pytest.fail("File change was not detected within timeout")

    # Verify the new file is now in the list
    new_files = {k["name"] for k in file_list.files}
    assert "new_file.txt" in new_files
    assert "initial.txt" in new_files

    rc.close()


@pytest.mark.asyncio
async def test_file_browser_watch_detects_deleted_file(tmpdir: Path):
    """Test that watch=True detects when a file is deleted."""
    tmpdir = Path(tmpdir)
    (tmpdir / "file1.txt").write_text("content1")
    (tmpdir / "file2.txt").write_text("content2")

    files_changed_event = asyncio.Event()

    @solara.component
    def Test():
        return solara.FileBrowser(tmpdir, watch=True)

    div, rc = solara.render_fixed(Test(), handle_error=False)
    file_list: solara.components.file_browser.FileListWidget = div.children[1]

    # Verify initial state
    initial_files = {k["name"] for k in file_list.files}
    assert "file1.txt" in initial_files
    assert "file2.txt" in initial_files

    # Set up observer
    def on_files_change(change):
        files_changed_event.set()

    file_list.observe(on_files_change, "files")

    # Give the watcher task a moment to start
    await asyncio.sleep(0.1)

    # Delete a file
    (tmpdir / "file2.txt").unlink()

    # Wait for the watcher to detect the change
    try:
        await asyncio.wait_for(files_changed_event.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pytest.fail("File deletion was not detected within timeout")

    # Verify file2 is gone
    new_files = {k["name"] for k in file_list.files}
    assert "file1.txt" in new_files
    assert "file2.txt" not in new_files

    rc.close()


def test_file_browser_selected_relative_path_after_full_path(tmpdir: Path):
    """Test that FileBrowser handles setting selected to a relative path after a full path.

    Regression test for issue where:
    1. User sets selected to a full path like /some/path/subdir/file.txt
    2. User then sets selected to a relative path like subdir/file.txt
    3. The current_dir would incorrectly become /some/path/subdir/subdir
       because the relative path's parent was appended to the existing directory.
    """
    tmpdir = Path(tmpdir)
    subdir = tmpdir / "subdir"
    subdir.mkdir()
    (subdir / "file.txt").write_text("content")

    selected = solara.reactive(cast(Optional[Path], None))

    @solara.component
    def Test():
        return solara.FileBrowser(tmpdir, selected=selected, can_select=True)

    div, rc = solara.render_fixed(Test(), handle_error=False)

    # First, set selected to a full path
    full_path = subdir / "file.txt"
    selected.value = full_path

    # Verify we're now in the subdir
    current_dir_text = div.children[0].children[0]
    assert str(subdir) in current_dir_text

    # Now set selected to a relative path (simulating user setting selected to "subdir/file.txt")
    # This should work and stay in the same subdir, not create /subdir/subdir
    relative_path = Path("subdir") / "file.txt"
    selected.value = relative_path

    # This should not raise FileNotFoundError
    # The current_dir should resolve relative to cwd, not to the previous current_dir
    rc.close()
