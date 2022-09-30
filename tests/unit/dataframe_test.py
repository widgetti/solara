import bqplot
import ipyvuetify as vw
import ipywidgets
import solara
import vaex.datasets
from solara.components.dataframe import (
    DropdownCard,
    FilterCard,
    HeatmapCard,
    HistogramCard,
    ScatterCard,
    SummaryCard,
    TableCard,
)
from solara.hooks.dataframe import provide_cross_filter, use_cross_filter

df = vaex.datasets.titanic()


def test_histogram_card():
    filter = set_filter = None

    @solara.component
    def FilterDummy():
        nonlocal filter, set_filter
        filter, set_filter = use_cross_filter(id(df), "test")
        return solara.Text("dummy")

    @solara.component
    def Test():
        provide_cross_filter()
        with solara.VBox() as main:
            HistogramCard(df, column="sex")
            FilterDummy()
        return main

    widget, rc = solara.render(Test(), handle_error=False)
    figure = rc._find(bqplot.Figure).widget
    bars = figure.marks[0]
    assert bars.x.tolist() == ["female", "male"]
    assert bars.y.tolist() == [466, 843]
    assert set_filter is not None
    set_filter(df["survived"] == True)  # noqa
    assert bars.x.tolist() == ["female", "male"]
    assert bars.y.tolist() == [339, 161]
    bars.selected = [0]
    assert df[filter].sex.unique() == ["female"]


def test_dropdown_card():
    filter = set_filter = None

    @solara.component
    def FilterDummy():
        nonlocal filter, set_filter
        filter, set_filter = use_cross_filter(id(df), "test")
        return solara.Text("dummy")

    @solara.component
    def Test(column=None):
        provide_cross_filter()
        with solara.VBox() as main:
            DropdownCard(df, column=column)
            FilterDummy()
        return main

    widget, rc = solara.render(Test(column="sex"), handle_error=False)
    select = rc._find(vw.Select)[0].widget
    result: list = select.items
    result.sort(key=lambda item: item["value"])
    assert result == [{"text": "female", "value": "female"}, {"text": "male", "value": "male"}]
    assert select.v_model is None
    select.v_model = {"text": "female", "value": "female"}
    assert df[filter].sex.unique() == ["female"]
    select.v_model = None
    assert filter is None
    assert set(df.sex.unique()) == {"female", "male"}


def testfilter_card():
    filter = set_filter = None

    @solara.component
    def FilterDummy():
        nonlocal filter, set_filter
        filter, set_filter = use_cross_filter(id(df), "test")
        return solara.Text("dummy")

    @solara.component
    def Test(column=None):
        provide_cross_filter()
        with solara.VBox() as main:
            FilterCard(df)
            FilterDummy()
        return main

    widget, rc = solara.render(Test(column="sex"), handle_error=False)
    textfield = rc._find(vw.TextField).widget
    assert textfield.v_model == ""
    textfield.v_model = "str_equals(sex, 'female')"
    assert filter is not None
    assert df[filter].sex.unique() == ["female"]
    textfield.v_model = None
    assert filter is None
    assert set(df.sex.unique()) == {"female", "male"}


def test_summary():
    filter = set_filter = None

    @solara.component
    def FilterDummy():
        nonlocal filter, set_filter
        filter, set_filter = use_cross_filter(id(df), "test")
        return solara.Text("dummy")

    @solara.component
    def Test():
        provide_cross_filter()
        with solara.VBox() as main:
            SummaryCard(df)
            FilterDummy()
        return main

    widget, rc = solara.render(Test(), handle_error=False)
    html = rc._find(vw.Html).widget
    assert html.children[0] == "1,309"
    assert set_filter is not None
    set_filter(df.sex == "female")
    assert html.children[0] == "466 / 1,309"


def test_table():
    filter = set_filter = None

    @solara.component
    def Test():
        nonlocal filter, set_filter
        provide_cross_filter()
        filter, set_filter = use_cross_filter(id(df), "test")
        return TableCard(df)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    output = widget.children[-1].children[-1]
    assert isinstance(output, ipywidgets.Output)
    # we can't test the output since no frontend is connected
    # assert output.outputs == ['a']
    assert set_filter is not None
    set_filter(df.sex == "female")
    # assert output.outputs == ['a']


def test_heatmap():
    filter = set_filter = None

    @solara.component
    def Test():
        nonlocal filter, set_filter
        provide_cross_filter()
        filter, set_filter = use_cross_filter(id(df), "test")
        return HeatmapCard(df, x="age", y="fare", debounce=False)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    figure = widget.children[-1].children[-1]
    assert isinstance(figure, bqplot.Figure)


def test_scatter():
    filter = set_filter = None

    @solara.component
    def FilterDummy():
        nonlocal filter, set_filter
        filter, set_filter = use_cross_filter(id(df), "test")
        return solara.Text("dummy")

    @solara.component
    def Test():
        provide_cross_filter()
        with solara.VBox() as main:
            ScatterCard(df, x="age", y="fare")
            FilterDummy()
        return main

    widget, rc = solara.render(Test(), handle_error=False)
    figure = rc._find(bqplot.Figure).widget
    scatter = figure.marks[0]
    scatter.selected = [0]
    assert filter is not None
    assert len(df[filter]) == 1
    scatter.selected = None
    assert filter is None
    scatter.selected = []
    assert filter is None
