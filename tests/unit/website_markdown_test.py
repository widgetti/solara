from pathlib import Path

import pytest

import solara
import solara.website
from solara.website.components.markdown import MarkdownWithMetadata

PAGES = Path(solara.website.__file__).parent / "pages"
MARKDOWN_FILES = sorted(path for path in PAGES.glob("**/*.md") if "---" in path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", MARKDOWN_FILES, ids=lambda path: str(path.relative_to(PAGES)))
def test_website_markdown_page_renders(path: Path):
    # a docs page with metadata must render, also when its body has more "---" (a table or a horizontal rule)
    box, rc = solara.render(MarkdownWithMetadata(path.read_text(encoding="utf-8"), unsafe_solara_execute=False), handle_error=False)
    rc.close()


def test_metadata_with_table_in_body():
    content = "---\ntitle: Test page\n---\n# Test page\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n---\n\nend\n"
    box, rc = solara.render(MarkdownWithMetadata(content, unsafe_solara_execute=False), handle_error=False)
    rc.close()
