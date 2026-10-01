import pytest

from solara.components.html_component_file import parse_component_html


def test_parse_component_html_preserves_section_bodies():
    template = '\n  <div title="A &amp; B">hello</div>\n'
    css = "\n  :host { color: red; }\n"
    script = "\n  export function mount() { return () => {}; }\n"
    source = f'<!-- component -->\n<template>{template}</template>\n<style>{css}</style>\n<script type="module">{script}</script>'

    parsed = parse_component_html(source, "greeting.html")

    assert parsed.template == template
    assert parsed.css == css
    assert parsed.script == script


def test_parse_component_html_allows_optional_sections():
    parsed = parse_component_html("<template><p>Hello</p></template>")
    assert parsed.template == "<p>Hello</p>"
    assert parsed.css is None
    assert parsed.script is None


@pytest.mark.parametrize(
    "source, message",
    [
        ("<style>x</style>", "template"),
        ("<template></template><template></template>", "duplicate"),
        ("<template></template><div></div>", "top-level"),
        ("<template></template><div/>", "top-level"),
        ("<template></template><script>run()</script>", 'type="module"'),
        ('<template></template><script type="text/javascript">run()</script>', 'type="module"'),
        ("<template><script>bad()</script></template>", "inside <template>"),
        ('<template><button onclick="bad()">x</button></template>', "inline event"),
        ("<template><div></template>", "mismatched"),
        ("<template><div></div>", "unclosed"),
    ],
)
def test_parse_component_html_rejects_invalid_sections(source, message):
    with pytest.raises(ValueError, match=message) as error:
        parse_component_html(source, "broken/component.html")
    assert "broken/component.html" in str(error.value)


def test_parse_component_html_rejects_duplicate_style_and_script():
    with pytest.raises(ValueError, match="duplicate"):
        parse_component_html("<template></template><style></style><style></style>", "duplicate.html")
    with pytest.raises(ValueError, match="duplicate"):
        parse_component_html('<template></template><script type="module"></script><script type="module"></script>', "duplicate.html")


def test_unclosed_element_error_includes_opening_location():
    with pytest.raises(ValueError, match=r"broken.html:2:3: unclosed <div>"):
        parse_component_html("<template>\n  <div>", "broken.html")
