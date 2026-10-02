from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

_BLOCKS = ("template", "style", "script")


@dataclass(frozen=True)
class ComponentFile:
    """The three parts of a single-file HTML component."""

    template: str
    css: str | None
    script: str | None


def parse_component_file(path: Path) -> ComponentFile:
    """Split a component file into its <template>, <style> and <script type="module"> parts.

    It reads the top level with the stdlib HTML tokenizer, like a browser: comments are skipped, <style> and
    <script> end at their first closing tag, and <template> ends at its matching </template>.
    """
    text = path.read_text(encoding="utf-8")
    parser = _BlockParser(text, path)
    parser.feed(text)
    parser.check_closed()
    blocks = parser.blocks

    if "template" not in blocks:
        raise ValueError(f"{path}: missing <template> block")
    if "script" in blocks and (blocks["script"][0].get("type") or "").strip().lower() != "module":
        raise ValueError(f'{path}: the <script> block needs type="module"')
    return ComponentFile(
        template=blocks["template"][1],
        css=blocks["style"][1] if "style" in blocks else None,
        script=blocks["script"][1] if "script" in blocks else None,
    )


class _BlockParser(HTMLParser):
    def __init__(self, text: str, path: Path):
        super().__init__(convert_charrefs=False)
        self.source = text
        self.path = path
        # getpos() gives (line, column); these map it to an offset in the text.
        self.line_starts = [0] + [i + 1 for i, char in enumerate(text) if char == "\n"]
        self.blocks: dict[str, tuple[dict[str, str | None], str]] = {}  # name -> (attributes, content)
        self.open_block: str | None = None
        self.open_attrs: dict[str, str | None] = {}
        self.content_start = 0
        self.depth = 0  # nested <template> blocks, the open one included

    def source_offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.open_block is None:
            if tag in _BLOCKS:
                if tag in self.blocks:
                    raise ValueError(f"{self.path}: more than one <{tag}> block")
                self.open_block, self.open_attrs, self.depth = tag, dict(attrs), 1
                self.content_start = self.source_offset() + len(self.get_starttag_text() or "")
        elif self.open_block == "template":
            if tag == "template":
                self.depth += 1
            elif tag in ("textarea", "title"):
                # A browser reads their content as text, so a tag inside them does not count.
                self.set_cdata_mode(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag != self.open_block:
            return
        self.depth -= 1
        if self.depth == 0:
            self.blocks[tag] = (self.open_attrs, self.source[self.content_start : self.source_offset()])
            self.open_block = None

    def check_closed(self) -> None:
        if self.open_block is not None:
            raise ValueError(f"{self.path}: unclosed <{self.open_block}> block")
        # The parser keeps an unclosed comment as unread text.
        if self.rawdata.startswith("<!--"):
            raise ValueError(f"{self.path}: unclosed <!-- comment")
