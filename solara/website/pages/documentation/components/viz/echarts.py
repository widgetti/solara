"""# Echarts"""

import solara
from solara.website.utils import apidoc

options = {
    "bars": {
        "title": {"text": "ECharts Getting Started Example"},
        "tooltip": {},
        "legend": {"data": ["sales"]},
        "xAxis": {"type": "category"},
        "yAxis": {},
        "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0, 0, 0, 0.5)"}},
        "series": [
            {
                "name": "sales",
                "type": "bar",
                "data": [
                    {"name": "Shirts", "value": 5},
                    {"name": "Cardigans", "value": 20},
                    {"name": "Chiffons", "value": 36},
                    {"name": "Pants", "value": 10},
                    {"name": "Heels", "value": 10},
                    {"name": "Socks", "value": 20},
                ],
                "universalTransition": True,
            }
        ],
    },
    "pie": {
        "title": {"text": "ECharts Getting Started Example"},
        "tooltip": {},
        "legend": {"data": ["sales"]},
        "series": [
            {
                "name": "sales",
                "type": "pie",
                "radius": [0, "50%"],
                "data": [
                    {"name": "Shirts", "value": 5},
                    {"name": "Cardigans", "value": 20},
                    {"name": "Chiffons", "value": 36},
                    {"name": "Pants", "value": 10},
                    {"name": "Heels", "value": 10},
                    {"name": "Socks", "value": 20},
                ],
                "universalTransition": True,
            }
        ],
    },
}


@solara.component
def Page():
    option = solara.use_reactive("bars")
    click_data = solara.use_reactive(None)
    mouseover_data = solara.use_reactive(None)
    mouseout_data = solara.use_reactive(None)

    with solara.Card("Echarts"):
        with solara.ToggleButtonsSingle(value=option.value, on_value=lambda data: setattr(option, "value", data)):
            solara.Button("bars", value="bars")
            solara.Button("pie", value="pie")
        solara.FigureEcharts(option=options[option.value], on_click=lambda e: setattr(click_data, "value", e), on_mouseover=lambda e: setattr(mouseover_data, "value", e), on_mouseout=lambda e: setattr(mouseout_data, "value", e), responsive=True)
    with solara.Card("Event data"):
        solara.Markdown(f"**Click data**: {click_data.value}")
        solara.Markdown(f"**Mouseover data**: {mouseover_data.value}")
        solara.Markdown(f"**Mouseout data**: {mouseout_data.value}")


__doc__ += apidoc(solara.FigureEcharts.f)  # type: ignore
