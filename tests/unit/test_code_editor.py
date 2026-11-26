from solara.widgets.code_editor import CodeEditorWidget


def test_code_editor_defaults():
    widget = CodeEditorWidget()
    assert widget.value == ""
    assert widget.language == "python"
    assert widget.theme == "default"
    assert widget.height == "240px"
    assert widget.read_only is False
    assert widget.line_numbers is True
    assert widget.tab_size == 4


def test_code_editor_element_roundtrip():
    widget = CodeEditorWidget.element(value="print('hi')", language="python", read_only=True)
    assert widget.kwargs["value"] == "print('hi')"
    assert widget.kwargs["language"] == "python"
    assert widget.kwargs["read_only"] is True
