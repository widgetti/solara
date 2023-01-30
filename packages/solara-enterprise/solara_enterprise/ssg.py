import logging
import multiprocessing.pool
import threading
import time
import typing
from pathlib import Path
from typing import List, Optional

import solara
from rich import print as rprint
from solara.server import settings
from typing_extensions import TypedDict

from . import license

logger = logging.getLogger("solara.server.ssg")

if typing.TYPE_CHECKING:
    import playwright.sync_api
    import playwright.sync_api._context_manager


class Playwright(threading.local):
    browser: Optional["playwright.sync_api.Browser"] = None
    sync_playwright: Optional["playwright.sync_api.Playwright"] = None
    context_manager: Optional["playwright.sync_api._context_manager.PlaywrightContextManager"] = None


pw = Playwright()
playwrights: List[Playwright] = []


class SSGData(TypedDict):
    title: str
    html: str
    styles: List[str]
    metas: List[str]


def _get_playwright():
    if hasattr(pw, "browser") and pw.browser is not None:
        return pw
    from playwright.sync_api import sync_playwright

    pw.context_manager = sync_playwright()
    pw.sync_playwright = pw.context_manager.start()

    pw.browser = pw.sync_playwright.chromium.launch(headless=not settings.ssg.headed)
    return pw


def ssg_crawl(base_url: str):
    license.check("SSG")
    import solara.server.app
    import solara.server.kernel

    build_path = settings.ssg.build_path
    assert build_path is not None
    build_path.mkdir(exist_ok=True)

    app_script = solara.server.app.apps["__default__"]
    rprint(f"Building {app_script.name} at {build_path}")
    routes = app_script.routes

    # although in theory we should be able to run this with multiple threads
    # there are issues with uvloop:
    #  e.g.: "Racing with another loop to spawn a process."
    thread_pool = multiprocessing.pool.ThreadPool(1)

    results = []
    for route in routes:
        results.append(thread_pool.apply_async(ssg_crawl_route, [f"{base_url}/", route, build_path, thread_pool]))

    def wait(async_result):
        results = async_result.get()
        for result in results:
            wait(result)

    for result in results:
        wait(result)
    thread_pool.terminate()
    for pw in playwrights:
        assert pw.browser is not None
        assert pw.context_manager is not None
        pw.browser.close()
        pw.context_manager.stop()

    rprint("Done building SSG")


def ssg_crawl_route(base_url: str, route: solara.Route, build_path: Path, thread_pool: multiprocessing.pool.ThreadPool):
    # if route
    url = base_url + (route.path if route.path != "/" else "")
    if not route.children:
        rprint("Check SSG for URL", url)
        build_path.mkdir(exist_ok=True, parents=True)
        path = build_path / ("index.html" if route.path == "/" else route.path + ".html")
        stale = False
        pw = _get_playwright()
        browser = pw.browser
        if path.exists():
            if route.file is None:
                rprint(f"File corresponding to {url} is not found (route: {route})")
            else:
                assert route.file is not None
                stale = path.stat().st_mtime < route.file.stat().st_mtime
                if stale:
                    rprint(f"Path {path} is stale: mtime {path} is older than {route.file} mtime {route.file.stat().st_mtime}")
        if not path.exists() or stale:
            rprint(f"Will generate {path}")
            page = browser.new_page()
            response = page.goto(url, wait_until="networkidle")
            if response.status != 200:
                raise Exception(f"Failed to load {url} with status {response.status}")
            # TODO: if we don't want to detached, we get stack trace showing errors in solara
            # make sure the html is loaded
            try:
                page.locator("#app").wait_for()
                # make sure vue took over
                page.locator("#pre-rendered-html-present").wait_for(state="detached")
                # and wait for the
                page.locator("text=Loading app").wait_for(state="detached")
                page.locator("#kernel-busy-indicator").wait_for(state="hidden")
                # page.wait_
                time.sleep(0.5)
                html = page.content()
            except Exception:
                logger.exception("Failure retrieving content for url: %s", url)
                raise
            path.write_text(html, encoding="utf-8")
            rprint(f"Wrote to {path}")
            page.close()
        else:
            rprint(f"Skipping existing render: {path}")
    results = []
    for child in route.children:
        result = thread_pool.apply_async(ssg_crawl_route, [url + "/", child, build_path / Path(route.path), thread_pool])
        results.append(result)
    return results


def ssg_data(path: str) -> Optional[SSGData]:
    license.check("SSG")
    html = ""
    # pre_rendered_css = ""
    styles = []
    title = "Solara ☀️"
    # still not sure why we sometimes end with a double slash
    if path.endswith("//"):
        path = path[:-2]
    if path.endswith("/"):
        path = path[:-1]
    if path.startswith("/"):
        # remove / so we don't get absolute paths on disk
        path = path[1:]
    # TODO: how do we know the app?
    build_path = settings.ssg.build_path
    if build_path and settings.ssg.enabled:
        html_path = build_path / path
        if (html_path / "index.html").exists():
            html_path = html_path / "index.html"
        else:
            html_path = html_path.with_suffix(".html")
        if html_path.exists() and html_path.is_file():
            logger.info("Using pre-rendered html at %r", html_path)

            from bs4 import BeautifulSoup, Tag

            soup = BeautifulSoup(html_path.read_text("utf8"), "html.parser")
            node = soup.find(id="app")
            # TODO: add classes...
            if node and isinstance(node, Tag):
                # only render children
                html = "".join(str(x) for x in node.contents)
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.text

            # include all meta tags
            rendered_metas = soup.find_all("meta")
            metas = []
            for meta in rendered_metas:
                # but only the ones added by solara
                if meta.attrs.get("data-solara-head-key"):
                    metas.append(str(meta))

            # include all styles
            rendered_styles = soup.find_all("style")
            for style in rendered_styles:
                style_html = str(style)
                # in case we want to skip the mathjax css
                # if "MJXZERO" in style_html:
                #     continue
                # pre_rendered_css += style_html
                styles.append(style_html)
                logger.debug("Include style (size is %r mb):\n\t%r", len(style_html) / 1024**2, style_html[:200])
            return SSGData(title=title, html=html, styles=styles, metas=metas)
        else:
            logger.error("Count not find html at %r", html_path)
    return None
