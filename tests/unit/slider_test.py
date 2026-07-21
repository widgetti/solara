from typing import Any, List, Optional

import ipyvuetify as vw

import solara
from solara.util import IPYVUETIFY_V3


def get_tick_labels(clazz, min, max, step, **kwargs) -> Optional[List[Any]]:
    el = clazz(label="label", min=min, max=max, step=step, **kwargs)
    _, rc = solara.render(el, handle_error=False)
    switch = rc.find(vw.Slider)
    if IPYVUETIFY_V3:
        labels = switch.widget.ticks if switch.widget.show_ticks else None
    else:
        labels = switch.widget.tick_labels
    rc.close()

    return labels


def test_int_slider():
    reference_ticks = [3, 4, 5]
    assert get_tick_labels(solara.IntSlider, 3, 5, 1, tick_labels="end_points") == ["3", "", "5"]
    assert get_tick_labels(solara.IntSlider, 3, 5, 1, tick_labels=True) == ["3", "4", "5"]
    assert get_tick_labels(solara.IntSlider, 3, 5, 1) is None
    assert get_tick_labels(solara.IntSlider, 3, 5, 1, tick_labels=reference_ticks) == reference_ticks


def test_float_slider():
    reference_ticks = [3.0, 3.5, 4.0, 4.5, 5.0]
    middle_empty_str = [""] * (len(reference_ticks) - 2)
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.5, tick_labels="end_points") == ["3", *middle_empty_str, "5"]
    tick_labels = get_tick_labels(solara.FloatSlider, 3, 5, 0.5, tick_labels=True)
    assert tick_labels is not None
    assert list(map(float, tick_labels)) == reference_ticks
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.5) is None
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.5, tick_labels=reference_ticks) == reference_ticks

    reference_ticks = [3, 3.3, 3.6, 3.9, 4.2, 4.5, 4.8, 5]
    middle_empty_str = [""] * (len(reference_ticks) - 2)
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.3, tick_labels="end_points") == ["3", *middle_empty_str, "5"]
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.3) is None
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.3, tick_labels=reference_ticks) == reference_ticks


def test_value_slider_uses_version_specific_ticks_and_accepts_float_index():
    value = solara.reactive("two")
    _, rc = solara.render(solara.SliderValue("value", value=value, values=["one", "two", "three"]), handle_error=False)
    slider = rc.find(vw.Slider).widget

    if IPYVUETIFY_V3:
        assert slider.ticks == {0: "one", 1: "two", 2: "three"}
        assert slider.step == 1
        slider.v_model = 2.0
    else:
        assert slider.tick_labels == ["one", "two", "three"]
        slider.v_model = 2

    assert value.value == "three"
    rc.close()
