import asyncio
from pathlib import Path

import playwright.sync_api

import solara
import solara.server.starlette

HERE = Path(__file__).parent


@solara.component
def Page():
    def run_async():
        async def some_task():
            await asyncio.sleep(0.01)
            label.value = "asyncio run"

        asyncio.create_task(some_task())

    label = solara.use_reactive("initial")
    solara.Button(label.value, on_click=run_async)


def test_async_callback(page_session: playwright.sync_api.Page, solara_app, extra_include_path, solara_server):
    with extra_include_path(HERE), solara_app("async_test"):
        page_session.goto(solara_server.base_url + "/")
        page_session.locator("text=initial").click()
        page_session.locator("text=asyncio run").wait_for()
