"""Parser for Solara's single-file native HTML component format."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class ComponentHTML:
    template: str
    css: str | None
    script: str | None


_VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_SECTIONS = {"template", "style", "script"}


class _ComponentParser(HTMLParser):
    def __init__(self, source: str, filename: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.filename = filename
        self.line_offsets = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self.line_offsets.append(index + 1)
        self.stack: list[tuple[str, str | None, int, int]] = []
        self.sections: dict[str, str] = {}
        self.section_start: dict[str, int] = {}

    def fail(self, message: str) -> None:
        line, column = self.getpos()
        raise ValueError(f"{self.filename}:{line}:{column + 1}: {message}")

    def source_offset(self) -> int:
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        parent_section = self.stack[0][1] if self.stack else None
        current_section: str | None
        if not self.stack:
            if tag not in _SECTIONS:
                self.fail(f'unexpected top-level <{tag}>; expected <template>, optional <style>, and optional <script type="module">')
            if tag in self.sections or tag in self.section_start:
                self.fail(f"duplicate top-level <{tag}> section")
            attr_map = {name.lower(): value for name, value in attrs}
            if tag == "template" and attrs:
                self.fail("<template> does not accept attributes")
            if tag == "style" and attrs:
                self.fail("<style> does not accept attributes")
            if tag == "script" and (set(attr_map) != {"type"} or (attr_map["type"] or "").lower() != "module"):
                self.fail('top-level <script> must have exactly type="module"')
            self.section_start[tag] = self.source_offset() + len(self.get_starttag_text() or "")
            current_section = tag
        else:
            current_section = parent_section
            if parent_section == "template":
                if tag == "script":
                    self.fail("<script> elements are not allowed inside <template>")
                for name, _ in attrs:
                    if name.lower().startswith("on"):
                        self.fail(f"inline event attribute {name!r} is not allowed")
        if tag not in _VOID_ELEMENTS:
            line, column = self.getpos()
            self.stack.append((tag, current_section, line, column + 1))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SECTIONS:
            self.fail("component sections must have explicit closing tags")
        if not self.stack:
            self.fail(f'unexpected top-level <{tag}>; expected <template>, optional <style>, and optional <script type="module">')
        if self.stack and self.stack[0][1] == "template":
            for name, _ in attrs:
                if name.lower().startswith("on"):
                    self.fail(f"inline event attribute {name!r} is not allowed")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self.stack:
            self.fail(f"unexpected closing tag </{tag}>")
        open_tag, section, _, _ = self.stack[-1]
        if tag != open_tag:
            self.fail(f"mismatched closing tag </{tag}>; expected </{open_tag}>")
        end_offset = self.source_offset()
        self.stack.pop()
        if not self.stack and section is not None:
            self.sections[section] = self.source[self.section_start[section] : end_offset]

    def handle_data(self, data: str) -> None:
        if not self.stack and data.strip():
            self.fail("unexpected text outside component sections")

    def handle_entityref(self, name: str) -> None:
        if not self.stack:
            self.fail("unexpected entity outside component sections")

    def handle_charref(self, name: str) -> None:
        if not self.stack:
            self.fail("unexpected character reference outside component sections")

    def handle_comment(self, data: str) -> None:
        pass

    def handle_decl(self, decl: str) -> None:
        self.fail("unexpected declaration outside component sections")

    def handle_pi(self, data: str) -> None:
        self.fail("unexpected processing instruction")

    def unknown_decl(self, data: str) -> None:
        self.fail(f"unsupported declaration {data!r}")


def parse_component_html(source: str, filename: str = "<string>") -> ComponentHTML:
    """Parse a component file while preserving the exact text inside each section."""
    parser = _ComponentParser(source, filename)
    try:
        parser.feed(source)
        parser.close()
    except ValueError as error:
        if filename in str(error):
            raise
        raise ValueError(f"{filename}: malformed HTML: {error}") from error
    if parser.stack:
        unclosed, _, line, column = parser.stack[-1]
        raise ValueError(f"{filename}:{line}:{column}: unclosed <{unclosed}> element")
    if "template" not in parser.sections:
        raise ValueError(f"{filename}: exactly one top-level <template> section is required")
    return ComponentHTML(
        template=parser.sections["template"],
        css=parser.sections.get("style"),
        script=parser.sections.get("script"),
    )
