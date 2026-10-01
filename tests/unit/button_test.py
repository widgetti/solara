import ipyvuetify as v
import pytest

import solara
from solara.util import IPYVUETIFY_V3


@pytest.mark.parametrize(
    ("text", "outlined", "variant"),
    [
        (False, False, "elevated"),
        (True, False, "text"),
        (False, True, "outlined"),
    ],
)
def test_button_style_api(text: bool, outlined: bool, variant: str):
    widget, rc = solara.render_fixed(solara.Button("Label", text=text, outlined=outlined), handle_error=False)
    try:
        if IPYVUETIFY_V3:
            assert widget.variant == variant
        else:
            assert widget.text is text
            assert widget.outlined is outlined
    finally:
        rc.close()


def test_button_icon_and_value_api():
    widget, rc = solara.render_fixed(solara.Button("Label", icon_name="mdi-home", value="choice"), handle_error=False)
    try:
        icon = widget.children[0]
        assert isinstance(icon, v.Icon)
        if IPYVUETIFY_V3:
            assert icon.start is True
            assert widget.value == "choice"
        else:
            assert icon.left is True
    finally:
        rc.close()


def test_icon_button_click_without_on_click():
    widget, rc = solara.render_fixed(solara.IconButton(icon_name="mdi-thumb-up"), handle_error=False)
    try:
        widget.fire_event("click")
    finally:
        rc.close()


def test_icon_button_click_with_on_click():
    clicked = False

    def on_click():
        nonlocal clicked
        clicked = True

    widget, rc = solara.render_fixed(solara.IconButton(icon_name="mdi-thumb-up", on_click=on_click), handle_error=False)
    try:
        widget.fire_event("click")
        assert clicked is True
    finally:
        rc.close()


def test_button_click_without_on_click():
    widget, rc = solara.render_fixed(solara.Button("Label"), handle_error=False)
    try:
        widget.fire_event("click")
    finally:
        rc.close()
