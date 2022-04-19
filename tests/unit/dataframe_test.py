import bqplot
import ipyvuetify as vw
import ipywidgets
import react_ipywidgets as react
import vaex.datasets

from solara.components.dataframe import (
    DropdownCard,
    FilterCard,
    HeatmapCard,
    HistogramCard,
    PivotTableCard,
    ScatterCard,
    SummaryCard,
    TableCard,
)
from solara.hooks.dataframe import provide_crossfilter, use_cross_filter
from solara.kitchensink import sol
from solara.widgets import PivotTable

df = vaex.datasets.titanic()


def test_histogram_card():
    filter = set_filter = None

    @react.component
    def Test():
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = use_cross_filter("test")
        return HistogramCard(df, column="sex")

    widget, rc = react.render_fixed(Test(), handle_error=False)
    figure = widget.children[-1].children[-1]
    assert isinstance(figure, bqplot.Figure)
    bars = figure.marks[0]
    assert bars.x.tolist() == ["female", "male"]
    assert bars.y.tolist() == [466, 843]
    assert set_filter is not None
    set_filter(df["survived"] == True)  # noqa
    assert bars.x.tolist() == ["female", "male"]
    assert bars.y.tolist() == [339, 161]
    bars.selected = [0]
    assert df[filter].sex.unique() == ["female"]


def test_pivot_table():
    filter = set_filter = None

    @react.component
    def Test():
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = use_cross_filter("test")
        return PivotTableCard(df, x=["sex"], y=["survived"])

    widget, rc = react.render_fixed(Test(), handle_error=False)
    pt = widget.children[-1].children[-1]
    assert isinstance(pt, PivotTable)
    data = pt.d
    assert data["x"] == ["sex"]
    assert data["y"] == ["survived"]
    assert data["values_x"] == ["466", "843"]
    assert data["values_y"] == ["809", "500"]
    assert data["values"] == [["127", "339"], ["682", "161"]]
    assert data["total"] == f"{len(df):,}"
    assert set_filter is not None
    set_filter(df["pclass"] == 2)
    data = pt.d
    assert data["values_x"] == ["106", "171"]
    assert data["values_y"] == ["158", "119"]
    assert data["values"] == [["12", "94"], ["146", "25"]]
    assert data["total"] == f"{len(df[df.pclass==2]):,}"
    set_filter(None)
    pt.selected = {"x": [0, 0]}  # sex, female
    assert filter is not None
    assert df[filter].sex.unique() == ["female"]

    pt.selected = {"y": [0, 0]}  # survived, False
    assert filter is not None
    assert df[filter].survived.unique() == [False]


def test_dropdown_card():
    filter = set_filter = None

    @react.component
    def Test(column=None):
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = use_cross_filter("test")
        return DropdownCard(df, column=column)

    widget, rc = react.render_fixed(Test(column="sex"), handle_error=False)
    select = widget.children[-1].children[-1]
    assert isinstance(select, vw.Select)
    assert select.items == [{"text": "female", "value": "female"}, {"text": "male", "value": "male"}]
    assert select.v_model is None
    select.v_model = {"text": "female", "value": "female"}
    assert df[filter].sex.unique() == ["female"]
    select.v_model = None
    assert filter is None
    assert df.sex.unique() == ["female", "male"]


def testfilter_card():
    filter = set_filter = None

    @react.component
    def Test(column=None):
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = use_cross_filter("test")
        return FilterCard(df)

    widget, rc = react.render_fixed(Test(column="sex"), handle_error=False)
    textfield = widget.children[-1].children[-1]
    assert isinstance(textfield, vw.TextField)
    assert textfield.v_model == ""
    textfield.v_model = "str_equals(sex, 'female')"
    assert filter is not None
    assert df[filter].sex.unique() == ["female"]
    textfield.v_model = None
    assert filter == ""
    assert df.sex.unique() == ["female", "male"]


def test_summary():
    filter = set_filter = None

    @react.component
    def Test():
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = use_cross_filter("test")
        return SummaryCard(df)

    widget, rc = react.render_fixed(Test(), handle_error=False)
    html = widget.children[-1].children[-1]
    assert isinstance(html, vw.Html)
    assert html.children[0] == "1,309"
    assert set_filter is not None
    set_filter(df.sex == "female")
    assert html.children[0] == "466 / 1,309"


def test_table():
    filter = set_filter = None

    @react.component
    def Test():
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = use_cross_filter("test")
        return TableCard(df)

    widget, rc = react.render_fixed(Test(), handle_error=False)
    output = widget.children[-1].children[-1]
    assert isinstance(output, ipywidgets.Output)
    # we can't test the output since no frontend is connected
    # assert output.outputs == ['a']
    assert set_filter is not None
    set_filter(df.sex == "female")
    # assert output.outputs == ['a']


def test_heatmap():
    filter = set_filter = None

    @react.component
    def Test():
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = use_cross_filter("test")
        return HeatmapCard(df, x="age", y="fare", debounce=False)

    widget, rc = react.render_fixed(Test(), handle_error=False)
    figure = widget.children[-1].children[-1]
    assert isinstance(figure, bqplot.Figure)


def test_scatter():
    filter = set_filter = None

    @react.component
    def Test():
        nonlocal filter, set_filter
        provide_crossfilter()
        filter, set_filter = sol.use_cross_filter("test")
        return ScatterCard(df, x="age", y="fare")

    widget, rc = react.render_fixed(Test(), handle_error=False)
    figure = widget.children[-1].children[-1]
    assert isinstance(figure, bqplot.Figure)
    scatter = figure.marks[0]
    scatter.selected = [0]
    assert filter is not None
    assert len(df[filter]) == 1
    scatter.selected = None
    assert filter is None
    scatter.selected = []
    assert filter is None
