from pathlib import Path

from ipyvuetify import Btn

import solara
from solara.components.file_download import FileDownloadWidget


def test_download(tmpdir: Path):
    _, rc = solara.render(solara.FileDownload(data="test content"), handle_error=False)
    assert rc.find(FileDownloadWidget).widget.filename == "solara-download.dat"
    assert rc.find(FileDownloadWidget).widget.bytes is None
    # lazily upload the data
    rc.find(FileDownloadWidget).widget.request_download = True
    rc.find(FileDownloadWidget, bytes=b"test content").wait_for()
    assert rc.find(Btn).widget.children[1] == "Download: solara-download.dat"

    # change the data
    rc.render(solara.FileDownload(data="test content2"))
    # it should 'reset'
    rc.find(FileDownloadWidget).widget.request_download = False
    assert rc.find(FileDownloadWidget).widget.bytes is None
    rc.find(FileDownloadWidget).widget.request_download = True
    rc.find(FileDownloadWidget, bytes=b"test content2").wait_for()

    filename = tmpdir / "test.txt"
    filename.write_text("test content3", encoding="utf-8")
    rc.render(solara.FileDownload(data=filename.open("rb")))
    assert rc.find(Btn).widget.children[1] == "Download: test.txt"
    rc.find(FileDownloadWidget).widget.request_download = True
    rc.find(FileDownloadWidget, bytes=b"test content3").wait_for()

    lazy_read_calls = 0

    def lazy_read():
        nonlocal lazy_read_calls
        lazy_read_calls += 1
        return b"lazy read"

    rc.render(solara.FileDownload(data=lazy_read))
    assert rc.find(Btn).widget.children[1] == "Download: solara-download.dat"
    assert lazy_read_calls == 0
    rc.find(FileDownloadWidget).widget.request_download = True
    assert lazy_read_calls == 1
    rc.find(FileDownloadWidget, bytes=b"lazy read").wait_for()
