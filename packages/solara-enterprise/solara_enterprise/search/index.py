import json
from pathlib import Path
from typing import Any, List

import solara
from rich import print as rprint
from solara.server import settings
from typing_extensions import TypedDict

from .. import license


class DocumentData(TypedDict):
    id: str
    text: str
    location: str
    title: str


def build_index(base_url: str):
    license.check("search")
    import solara.server.app
    import solara.server.kernel

    build_path = settings.ssg.build_path
    assert build_path is not None
    app_script = solara.server.app.apps["__default__"]
    rprint(f"Building search index for {app_script.name} by using {build_path}")
    routes = app_script.routes

    documents: List[DocumentData] = []

    for route in routes:
        add_document(f"{base_url}/", route, build_path, documents)
    index_file = app_script.directory.parent / "assets" / "search.json"
    rprint("Writing search index to", index_file)
    with open(index_file, "w") as f:
        json.dump(documents, f, indent=4)


def add_document(base_url: str, route: solara.Route, build_path: Path, documents: List[DocumentData]):
    url = base_url + (route.path if route.path != "/" else "")
    if not route.children:
        path = build_path / ("index.html" if route.path == "/" else route.path + ".html")
        rprint("Processing", path)
        from bs4 import BeautifulSoup  # , Tag

        if not path.exists():
            rprint(f"Warning: {path} does not exist")
        else:
            soup = BeautifulSoup(path.read_text("utf8"), "html.parser")
            node = soup.find(class_="solara-page-content-search")

            if node is None:
                rprint(f"Warning: {path} has no solara-page-content-search")
            else:
                # split by h1 and h2
                parts: List[List[Any]] = [[]]
                ids = [None]
                titles = [soup.title.string if soup.title else ""]
                current = parts[-1]
                # remove invisible title elements
                for el in node.find_all("span", attrs={"style": "display: none;"}):
                    el.string = ""
                for el in node.descendants:
                    if el.name == "h1" or el.name == "h2":
                        ids.append(el.get("id"))
                        parts.append([])
                        titles.append(el.string)
                        current = parts[-1]
                    else:
                        current.append(el)
                # join the next node
                text = ""
                for i, part in enumerate(parts):
                    for el in part:
                        if el.string:
                            text += el.string.strip() + " "
                    # texts.append("")
                    id = ids[i]
                    location = f"{url}#{id}" if id else url
                    text = text.strip()
                    title = titles[i].strip()
                    if title != text:
                        documents.append({"id": id, "text": text, "location": location, "title": title})
                    text = ""
                # documents.append({"id": url, "html": str(node), "location": url})
    for child in route.children:
        add_document(url + "/", child, build_path / Path(route.path), documents)
