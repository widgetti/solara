from pathlib import Path

import pytest

from solara_html.parse import ComponentFile, parse_component_file


def test_parse_template_only(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text("<template><p>Hello</p></template>", encoding="utf-8")

    component = parse_component_file(path)

    assert component == ComponentFile(template="<p>Hello</p>", css=None, script=None)


def test_parse_optional_style_and_module_script(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text(
        """
<template>
  <button data-solara-event-click="reset">Reset</button>
</template>
<style>
  button { color: rebeccapurple; }
</style>
<script type="module">
  export function mount() {}
</script>
""".strip(),
        encoding="utf-8",
    )

    component = parse_component_file(path)

    assert 'data-solara-event-click="reset"' in component.template
    assert component.css == "\n  button { color: rebeccapurple; }\n"
    assert component.script == "\n  export function mount() {}\n"


def test_parse_nested_template(tmp_path: Path):
    path = tmp_path / "nested.html"
    path.write_text(
        "<template><div><template>Inner</template></div></template>",
        encoding="utf-8",
    )

    component = parse_component_file(path)

    assert component.template == "<div><template>Inner</template></div>"


def test_parse_requires_template_with_file_name(tmp_path: Path):
    path = tmp_path / "missing.html"
    path.write_text("<style>p { color: red; }</style>", encoding="utf-8")

    with pytest.raises(ValueError, match="missing.html"):
        parse_component_file(path)


def test_parse_style_with_attributes(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text('<template><p>Hi</p></template><style media="screen">p { color: red; }</style>', encoding="utf-8")

    assert parse_component_file(path).css == "p { color: red; }"


def test_parse_rejects_classic_script(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text("<template><p>Hi</p></template><script>export function mount() {}</script>", encoding="utf-8")

    with pytest.raises(ValueError, match='type="module"'):
        parse_component_file(path)


def test_parse_template_string_in_script(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text(
        '<template><p>Hi</p></template>\n<script type="module">const t = "<template>x</template>";</script>',
        encoding="utf-8",
    )

    component = parse_component_file(path)

    assert component.template == "<p>Hi</p>"
    assert component.script == 'const t = "<template>x</template>";'


def test_parse_style_string_in_script(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text(
        "<template><p>Hi</p></template><script type='module'>const s = \"<style>p {}</style>\";</script>",
        encoding="utf-8",
    )

    component = parse_component_file(path)

    assert component.css is None
    assert component.script == 'const s = "<style>p {}</style>";'


def test_parse_skips_top_level_comments(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text("<!-- <template>Old</template> --><template><!-- </template> --><p>New</p></template>", encoding="utf-8")

    assert parse_component_file(path).template == "<!-- </template> --><p>New</p>"


@pytest.mark.parametrize("name", ["template", "style", "script"])
def test_parse_rejects_duplicate_block(tmp_path: Path, name: str):
    path = tmp_path / "hello.html"
    block = '<script type="module"></script>' if name == "script" else f"<{name}></{name}>"
    path.write_text("<template><p>Hi</p></template>" + block * (2 if name != "template" else 1), encoding="utf-8")

    with pytest.raises(ValueError, match=f"more than one <{name}>"):
        parse_component_file(path)


@pytest.mark.parametrize(
    "text, block",
    [
        ("<template><p>Hi</p>", "<template>"),
        ("<template><template></template>", "<template>"),
        ("<template></template><style>p {}", "<style>"),
        ('<template></template><script type="module">', "<script>"),
        ("<template></template><!-- note", "<!--"),
    ],
)
def test_parse_rejects_unclosed_block(tmp_path: Path, text: str, block: str):
    path = tmp_path / "hello.html"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match=f"unclosed {block}"):
        parse_component_file(path)


def test_parse_greater_than_in_quoted_attribute(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text('<template data-x="a>b"><p>Hi</p></template>', encoding="utf-8")

    assert parse_component_file(path).template == "<p>Hi</p>"


def test_parse_end_tag_in_attribute_value(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text('<template><p title="</template>">Hi</p></template>', encoding="utf-8")

    assert parse_component_file(path).template == '<p title="</template>">Hi</p>'


@pytest.mark.parametrize("tag", ["textarea", "title"])
def test_parse_end_tag_in_raw_text_element(tmp_path: Path, tag: str):
    path = tmp_path / "hello.html"
    path.write_text(f"<template><{tag}></template></{tag}>\n<p>Hi</p></template>", encoding="utf-8")

    assert parse_component_file(path).template == f"<{tag}></template></{tag}>\n<p>Hi</p>"


def test_parse_unquoted_module_script(tmp_path: Path):
    path = tmp_path / "hello.html"
    path.write_text("<template><p>Hi</p></template>\n<script type=module>export function mount() {}</script>", encoding="utf-8")

    assert parse_component_file(path).script == "export function mount() {}"
