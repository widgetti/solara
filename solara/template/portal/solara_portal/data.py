import dataclasses
from pathlib import Path
from typing import Any, Dict

import vaex.datasets
import yaml


@dataclasses.dataclass
class DataFrame:
    title: str
    df: Any
    image_url: str


dfs = {
    "titanic": DataFrame(
        df=vaex.datasets.titanic(),
        title="Titanic",
        image_url="https://images.unsplash.com/photo-1561625116-df74735458a5?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=3574&q=80",  # noqa
    ),
    "iris": DataFrame(
        df=vaex.datasets.iris(),
        title="Iris",
        image_url="https://images.unsplash.com/photo-1540163502599-a3284e17072d?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=3870&q=80",  # noqa
    ),
    "taxi": DataFrame(
        df=vaex.datasets.taxi(),
        title="New York Taxi",
        image_url="https://images.unsplash.com/photo-1514749204155-24e484635226?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1587&q=80",  # noqa
    ),
}

names = list(dfs)
# def load(name):
#     if name == "titanic"

HERE = Path(__file__)


@dataclasses.dataclass
class Article:
    markdown: str
    title: str
    description: str
    image_url: str


articles: Dict[str, Article] = {}

for file in (HERE.parent / "content/articles").glob("*.md"):
    content = file.read_text()
    lines = [k.strip() for k in content.split("\n")]
    frontmatter_start = lines.index("---", 0)
    frontmatter_end = lines.index("---", frontmatter_start + 1)
    yamltext = "\n".join(lines[frontmatter_start + 1 : frontmatter_end - 2])
    metadata = yaml.safe_load(yamltext)
    markdown = "\n".join(lines[frontmatter_end + 1 :])
    articles[file.name] = Article(markdown=markdown, title=metadata["title"], description=metadata["description"], image_url=metadata["image"])
