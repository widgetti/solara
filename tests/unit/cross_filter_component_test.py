import ipyvuetify as vw
import pytest
import vaex.datasets

import solara
import solara.lab
from solara.components.cross_filter import Select, magic_value_missing

df_vaex = vaex.datasets.titanic()
df_pandas = df_vaex.to_pandas_df()


@pytest.fixture(params=["pandas", "vaex"])
def df_titanic(request):
    named = {"vaex": df_vaex, "pandas": df_pandas}
    return named[request.param]


def test_cross_filter_select(df_titanic):
    filter = set_filter = None

    @solara.component
    def FilterDummy():
        nonlocal filter, set_filter
        filter, set_filter = solara.use_cross_filter(id(df_titanic), "test")
        return solara.Text("dummy")

    @solara.component
    def Test(column=None, max_unique=100, multiple=False):
        solara.provide_cross_filter()
        with solara.VBox() as main:
            solara.CrossFilterSelect(df_titanic, column=column, max_unique=max_unique, multiple=multiple)
            FilterDummy()
        return main

    widget, rc = solara.render(Test(column="sex"), handle_error=False)
    select = rc._find(Select).widget
    result: list = select.items
    result.sort(key=lambda item: item["value"])
    assert result == [{"text": "female", "value": "female", "count": 466, "count_max": 466}, {"text": "male", "value": "male", "count": 843, "count_max": 843}]
    assert select.value is None
    select.value = {"value": "female"}
    assert filter is not None

    df = df_titanic[filter]
    assert list(df.sex.unique()) == ["female"]
    select.value = None
    assert filter is None
    assert set(df_titanic.sex.unique()) == {"female", "male"}

    # test a column with missing values
    rc.render(Test(column="cabin", max_unique=200))
    result = select.items
    assert len(result) == 187
    result.sort(key=lambda item: item["value"])
    assert result[0] == {
        "text": "A10",
        "value": "A10",
        "count": 1,
        "count_max": 1,
    }
    assert result[-1] == {
        "text": "NA",
        "value": magic_value_missing,
        "count": 1014,
        "count_max": 1014,
    }
    assert select.value is None

    select.value = {"value": magic_value_missing}
    assert filter is not None
    df = df_titanic[filter]
    assert list(df.cabin.unique()) == [None]

    # changing column should clear filter
    rc.render(Test(column="boat"))
    assert filter is None

    # test a column with missing values
    rc.render(Test(column="sex", multiple=True))
    assert select is rc._find(Select).widget
    select.value = [{"value": "female"}]
    assert filter is not None
    df = df_titanic[filter]
    assert len(df) == 466

    select.value = [{"value": "female"}, {"value": "male"}]
    assert filter is not None
    df = df_titanic[filter]
    assert len(df) == 1309


def test_cross_filter_slider(df_titanic):
    filter = set_filter = None

    @solara.component
    def FilterDummy():
        nonlocal filter, set_filter
        filter, set_filter = solara.use_cross_filter(id(df_titanic), "test")
        return solara.Text("dummy")

    @solara.component
    def Test(column=None, max_unique=100, multiple=False):
        solara.provide_cross_filter()
        with solara.VBox() as main:
            solara.CrossFilterSlider(df_titanic, column=column)
            FilterDummy()
        return main

    widget, rc = solara.render(Test(column="pclass"), handle_error=False)
    assert filter is not None
    rc._find(vw.Alert).assert_empty()
    slider = rc._find(vw.Slider).widget
    assert slider.v_model == 1
    assert slider.min == 1
    assert slider.max == 3
    df = df_titanic[filter]
    assert df["pclass"].unique() == [1]

    slider.v_model = 2
    df = df_titanic[filter]
    assert df["pclass"].unique() == [2]

    rc.render(Test(column="age"))
    # will render a different slider
    slider = rc._find(vw.Slider).widget
    assert slider.v_model == 0.1667
    assert slider.min == 0.1667
    assert slider.max == 80
