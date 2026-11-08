import ipyvuetify as v

import solara


def test_scrollable_public_api():
    child = solara.Text("Long content")
    widget, rc = solara.render_fixed(
        solara.Scrollable(
            children=[child],
            max_height="300px",
            classes=["log-output"],
            style={"border": "1px solid"},
        ),
        handle_error=False,
    )
    try:
        assert isinstance(widget, v.Html)
        assert widget.tag == "div"
        assert len(widget.children) == 1
        assert isinstance(widget.children[0], v.Html)
        assert widget.children[0].children == ["Long content"]
        assert widget.class_ == "log-output"
        assert "max-height: 300px" in widget.style_
        assert "overflow-y: auto" in widget.style_
        assert "border:1px solid" in widget.style_
    finally:
        rc.close()
