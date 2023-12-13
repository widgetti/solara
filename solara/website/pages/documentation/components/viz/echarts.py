"""# Echarts

"""


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
    option, set_option = solara.use_state("bars")
    click_data, set_click_data = solara.use_state(None)
    mouseover_data, set_mouseover_data = solara.use_state(None)
    mouseout_data, set_mouseout_data = solara.use_state(None)

    with solara.VBox() as main:
        with solara.Card("Echarts"):
            with solara.ToggleButtonsSingle("bars", on_value=set_option):
                solara.Button("bars")
                solara.Button("pie")
            solara.FigureEcharts(option=options[option], on_click=set_click_data, on_mouseover=set_mouseover_data, on_mouseout=set_mouseout_data)
        with solara.Card("Event data"):
            solara.Markdown(f"**Click data**: {click_data}")
            solara.Markdown(f"**Mouseover data**: {mouseover_data}")
            solara.Markdown(f"**Mouseout data**: {mouseout_data}")

    return main


__doc__ += apidoc(solara.FigureEcharts.f)  # type: ignore
