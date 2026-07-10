import ipyvuetify as v

import solara
from solara.util import IPYVUETIFY_V3


def test_alert_props_match_installed_ipyvuetify():
    _, rc = solara.render(solara.Success("ok", dense=True), handle_error=False)
    widget = rc.find(v.Alert).widget
    if IPYVUETIFY_V3:
        assert widget.variant == "outlined"
        assert widget.density == "compact"
    else:
        assert widget.outlined is True
        assert widget.text is True
        assert widget.dense is True
    rc.close()

    _, rc = solara.render(solara.Success("ok", icon="mdi-check"), handle_error=False)
    widget = rc.find(v.Alert).widget
    if IPYVUETIFY_V3:
        assert widget.icon is None
        assert rc.find(v.Icon).widget.children == ["mdi-check"]
    else:
        assert widget.icon == "mdi-check"
    rc.close()


def test_progress_value_matches_installed_ipyvuetify():
    _, rc = solara.render(solara.ProgressLinear(42), handle_error=False)
    widget = rc.find(v.ProgressLinear).widget
    if IPYVUETIFY_V3:
        assert widget.model_value == 42
    else:
        assert widget.value == 42
    rc.close()


def test_input_props_match_installed_ipyvuetify():
    _, rc = solara.render(solara.InputText("text", dense=True), handle_error=False)
    widget = rc.find(v.TextField).widget
    assert (widget.density == "compact") if IPYVUETIFY_V3 else (widget.dense is True)
    rc.close()

    _, rc = solara.render(solara.InputTextArea("text", dense=True), handle_error=False)
    widget = rc.find(v.Textarea).widget
    if IPYVUETIFY_V3:
        assert widget.variant == "outlined"
        assert widget.density == "compact"
    else:
        assert widget.solo is True
        assert widget.outlined is True
        assert widget.dense is True
    rc.close()


def test_toggle_density_matches_installed_ipyvuetify():
    _, rc = solara.render(solara.ToggleButtonsSingle("one", values=["one", "two"], dense=True), handle_error=False)
    widget = rc.find(v.BtnToggle).widget
    assert (widget.density == "compact") if IPYVUETIFY_V3 else (widget.dense is True)
    rc.close()


def test_tooltip_props_match_installed_ipyvuetify():
    child = solara.Button("child")
    _, rc = solara.render(solara.Tooltip("tip", color="red", children=[child]), handle_error=False)
    tooltip = rc.find(v.Tooltip).widget
    button = rc.find(v.Btn).widget
    if IPYVUETIFY_V3:
        assert tooltip.location == "bottom"
        assert tooltip.content_props == {"style": "background-color: red;"}
        assert button.v_bind == "tooltip.props"
    else:
        assert tooltip.bottom is True
        assert tooltip.color == "red"
        assert button.v_on == "tooltip.on"
    rc.close()


def test_boolean_labels_are_not_duplicated_on_v3():
    _, rc = solara.render(solara.Column(children=[solara.Checkbox(label="check"), solara.Switch(label="switch")]), handle_error=False)
    checkbox = rc.find(v.Checkbox).widget
    switch = rc.find(v.Switch).widget
    expected = [] if IPYVUETIFY_V3 else ["check"]
    assert checkbox.children == expected
    expected = [] if IPYVUETIFY_V3 else ["switch"]
    assert switch.children == expected
    rc.close()


def test_details_uses_available_panel_components():
    _, rc = solara.render(solara.Details("summary", children=["details"]), handle_error=False)
    if IPYVUETIFY_V3:
        assert rc.find(v.ExpansionPanelTitle).widget.children == ["summary"]
        assert rc.find(v.ExpansionPanelText).widget.children == ["details"]
    else:
        assert rc.find(v.ExpansionPanelHeader).widget.children == ["summary"]
        assert rc.find(v.ExpansionPanelContent).widget.children == ["details"]
    rc.close()
