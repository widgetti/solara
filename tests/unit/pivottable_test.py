import vaex

import solara
import solara.components.pivot_table as pt
from solara.components.pivot_table import PivotTableWidget

from .common import repeat_while_false, repeat_while_true

df = vaex.datasets.titanic()


def test_df_data_pivot_data_vaex():
    dfg = pt.df_aggregate_vaex(df, ["sex"], {"count": solara.AggregationCount(type="count")})
    assert dfg["count"].tolist() == [466, 843]

    data = pt.df_aggregate_pivot_vaex(df, ["sex"], [], solara.AggregationCount(type="count"))
    assert data["values_x"] == ["466", "843"]
    assert data["values_y"] == []
    assert data["values"] == [[]]
    assert data["total"] == "1,309"

    data = pt.df_aggregate_pivot_vaex(df, [], ["sex"], solara.AggregationCount(type="count"))
    assert data["values_x"] == []
    assert data["values_y"] == ["466", "843"]
    assert data["values"] == [[]]
    assert data["total"] == "1,309"

    data = pt.df_aggregate_pivot_vaex(df, ["survived"], ["sex"], solara.AggregationCount(type="count"))
    assert data["values_x"] == ["809", "500"]
    assert data["values_y"] == ["466", "843"]
    assert data["values"] == [["127", "682"], ["339", "161"]]
    assert data["total"] == "1,309"


def test_df_data_pivot_table_view():
    data = pt.df_aggregate_pivot_vaex(df, ["survived"], ["sex"], solara.AggregationCount(type="count"))
    el = solara.PivotTableView(data=data)
    box, rc = solara.render(el, handle_error=False)
    assert rc._find(PivotTableWidget).widget.d["values"] == [["127", "682"], ["339", "161"]]


def test_df_data_pivot_table_df():
    el = solara.PivotTable(df, ["survived"], ["sex"])
    box, rc = solara.render(el, handle_error=False)
    repeat_while_false(lambda: rc._find(PivotTableWidget))
    assert rc.find(PivotTableWidget).widget.d["values"] == [["127", "682"], ["339", "161"]]

    el = solara.PivotTableCard(df, ["survived"], ["sex"])
    box, rc = solara.render(el, handle_error=False)
    repeat_while_false(lambda: rc._find(PivotTableWidget))
    assert rc.find(PivotTableWidget).widget.d["values"] == [["127", "682"], ["339", "161"]]


def test_pivot_table():
    filter = set_filter = None

    @solara.component
    def FilterDummy(df):
        nonlocal filter, set_filter
        filter, set_filter = solara.use_cross_filter(id(df), "test")
        return solara.Text("dummy")

    @solara.component
    def Test():
        solara.provide_cross_filter()
        with solara.VBox() as main:
            solara.PivotTableCard(df, x=["sex"], y=["survived"])
            FilterDummy(df)
        return main

    widget, rc = solara.render(Test(), handle_error=False)
    rc.find(PivotTableWidget).wait_for(timeout=10)
    pt = rc._find(PivotTableWidget).widget
    data = pt.d
    assert data["x"] == ["sex"]
    assert data["y"] == ["survived"]
    assert data["values_x"] == ["466", "843"]
    assert data["values_y"] == ["809", "500"]
    assert data["values"] == [["127", "339"], ["682", "161"]]
    assert data["total"] == f"{len(df):,}"
    assert set_filter is not None
    set_filter(str(df["pclass"] == 2))
    # wait for the data to change
    rc.find(PivotTableWidget).assert_wait(lambda w: w.d["values"] != [["127", "339"], ["682", "161"]], timeout=10)
    data = pt.d
    assert data["values_x"] == ["106", "171"]
    assert data["values_y"] == ["158", "119"]
    assert data["values"] == [["12", "94"], ["146", "25"]]
    assert data["total"] == f"{len(df[df.pclass==2]):,}"
    set_filter(None)
    # wait for the filter to be applied (data should change)
    rc.find(PivotTableWidget).assert_wait(lambda w: w.d["values"] != [["12", "94"], ["146", "25"]], timeout=10)
    pt.selected = {"x": [0, 0]}  # sex, female
    repeat_while_true(lambda: filter is None)
    assert df[df[str(filter)]].sex.unique() == ["female"]

    pt.selected = {"y": [0, 0]}  # survived, False
    assert filter is not None
    assert df[df[str(filter)]].survived.unique() == [False]
