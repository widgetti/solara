import logging
from pathlib import Path
from typing import List, Optional

import solara
from rich import print as rprint
from solara.server import settings
from typing_extensions import TypedDict

from . import license

logger = logging.getLogger("solara.server.ssg")


class SSGData(TypedDict):
    title: str
    html: str
    styles: List[str]


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

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not settings.ssg.headed)
        for route in routes:
            ssg_crawl_route(browser, f"{base_url}/", route, build_path)
        browser.close()


def ssg_crawl_route(browser, base_url: str, route: solara.Route, build_path: Path):
    # if route
    url = base_url + (route.path if route.path != "/" else "")
    rprint("Check SSG for URL", url)
    build_path.mkdir(exist_ok=True, parents=True)
    path = build_path / ("index.html" if route.path == "/" else route.path + ".html")
    if not path.exists():
        rprint(f"Will generate {path}")
        page = browser.new_page()
        response = page.goto(url, wait_until="networkidle")
        if response.status != 200:
            raise Exception(f"Failed to load {url} with status {response.status}")
        # TODO: if we don't want to detached, we get stack trace showing errors in solara
        # make sure the html is loaded
        page.locator("#app").wait_for()
        # make sure vue took over
        page.locator("#pre-rendered-html-present").wait_for(state="detached")
        # and wait for the
        page.locator("text=Loading app").wait_for(state="detached")
        html = page.content()
        path.write_text(html, encoding="utf-8")
        rprint(f"Wrote to {path}")
        page.close()
    else:
        rprint(f"Skipping existing render: {path}")
    for child in route.children:
        if child.path != "/":
            ssg_crawl_route(browser, url + "/", child, build_path / Path(route.path))


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
            return SSGData(title=title, html=html, styles=styles)
        else:
            logger.error("Looking for html at %r", html_path)
    return None
