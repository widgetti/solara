from pathlib import Path

import pandas as pd
import playwright
import playwright.sync_api


def test_download(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app, tmpdir: Path):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/file_download")
        with page_session.expect_download() as download_info:
            page_session.locator('button:has-text("Download file")').click()
        target = tmpdir / "downloaded.txt"
        download = download_info.value
        download.save_as(target)
        assert target.read_text(encoding="utf8") == "This is the content of the file"

        with page_session.expect_download() as download_info:
            page_session.locator('button:has-text("Download: users.csv")').click()
        target = tmpdir / "downloaded.csv"
        download = download_info.value
        download.save_as(target)
        df = pd.read_csv(target)
        assert df.to_dict() == {"id": {0: 1, 1: 2, 2: 3}, "name": {0: "John", 1: "Mary", 2: "Bob"}}
