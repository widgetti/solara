import ipyvuetify as vw

import solara


def get_tick_labels(clazz, min, max, step, **kwargs) -> list:
    el = clazz(label="label", min=min, max=max, step=step, **kwargs)
    _, rc = solara.render(el, handle_error=False)
    switch = rc.find(vw.Slider)
    labels = switch.widget.tick_labels
    rc.close()

    return labels


def test_int_slider():
    reference_ticks = [3, 4, 5]
    assert get_tick_labels(solara.IntSlider, 3, 5, 1) == ["3", None, "5"]
    assert get_tick_labels(solara.IntSlider, 3, 5, 1, tick_labels=None) == [None] * len(reference_ticks)
    assert get_tick_labels(solara.IntSlider, 3, 5, 1, tick_labels=reference_ticks) == map(str, reference_ticks)


def test_float_slider():
    reference_ticks = [3, 3.5, 4, 4.5, 5]
    middle_nones = [None] * (len(reference_ticks) - 2)
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.5) == ["3", *middle_nones, "5"]
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.5, tick_labels=None) == [None] * len(reference_ticks)
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.5, tick_labels=reference_ticks) == map(str, reference_ticks)

    reference_ticks = [3, 3.3, 3.6, 3.9, 4.2, 4.5, 4.8, 5]
    middle_nones = [None] * (len(reference_ticks) - 2)
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.3) == ["3", *middle_nones, "5"]
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.3, tick_labels=None) == [None] * len(reference_ticks)
    assert get_tick_labels(solara.FloatSlider, 3, 5, 0.3, tick_labels=reference_ticks) == map(str, reference_ticks)
