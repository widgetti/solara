import platform
import unittest.mock
from pathlib import Path

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

    div, rc = solara.render_fixed(Test())
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

    list.clicked = None
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
        return solara.FileBrowser(tmpdir, on_path_select=on_path_select, on_directory_change=on_directory_change, on_file_open=on_file_open, can_select=True)

    try:
        div, rc = solara.render_fixed(Test())

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
    assert names == {"unit", "ui", "integration", ".."}


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
    assert names == {"unit", "ui", "integration", ".."}
    file_list.test_click("..")
    assert mock.call_count == 0
    file_list.test_click("integration")
    items = file_list.files
    names = {k["name"] for k in items}
    assert names != {"unit", "ui", "integration", ".."}
    assert mock.call_count == 1
