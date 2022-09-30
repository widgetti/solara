from typing import Optional

import solara
import vaex

df = vaex.from_arrays(x=[0, 1, 2, 3, 4], y=[0, 1, 4, 9, 16])


def test_basic():
    set_filter1 = filter1 = None
    set_filter2 = filter2 = None

    @solara.component
    def FilterDummy1():
        nonlocal filter1, set_filter1
        filter1, set_filter1 = solara.use_cross_filter(id(df), "test1")
        return solara.Text("dummy1")

    @solara.component
    def FilterDummy2():
        nonlocal filter2, set_filter2
        filter2, set_filter2 = solara.use_cross_filter(id(df), "test1")
        return solara.Text("dummy2")

    @solara.component
    def Page():
        solara.provide_cross_filter()
        with solara.VBox() as main:
            FilterDummy1()
            FilterDummy2()
        return main

    rc, box = solara.render(Page(), handle_error=False)
    assert set_filter1 is not None
    assert set_filter2 is not None
    set_filter1(df.x > 1)
    assert filter1 is None
    assert filter2 is not None

    set_filter2(df.x > 4)
    assert filter1 is not None
    assert filter2 is not None

    set_filter2(None)
    assert filter1 is None
    assert filter2 is not None


def test_remove():
    set_filter1 = filter1 = None
    set_filter2 = filter2 = None
    set_multiple = None
    cross_filter_store: Optional[solara.hooks.dataframe.CrossFilterStore] = None

    @solara.component
    def FilterDummy1():
        nonlocal filter1, set_filter1
        filter1, set_filter1 = solara.use_cross_filter(id(df), "test1")
        return solara.Text("dummy1")

    @solara.component
    def FilterDummy2():
        nonlocal filter2, set_filter2
        filter2, set_filter2 = solara.use_cross_filter(id(df), "test1")
        return solara.Text("dummy2")

    @solara.component
    def Page():
        nonlocal cross_filter_store, set_multiple
        multiple, set_multiple = solara.use_state(True)
        cross_filter_store = solara.provide_cross_filter()
        with solara.VBox() as main:
            if multiple:
                FilterDummy1()
                FilterDummy2()
            else:
                FilterDummy1()
        return main

    rc, box = solara.render(Page(), handle_error=False)
    assert set_multiple is not None
    assert set_filter1 is not None
    assert set_filter2 is not None
    assert cross_filter_store is not None
    set_filter1(df.x > 1)
    filters = cross_filter_store.filters[id(df)]
    assert len(filters) == 1
    set_filter2(df.x < 4)
    assert len(filters) == 2
    set_multiple(False)
    assert len(filters) == 1
    set_multiple(True)
    # trigger a remove which did not add a filter
    set_multiple(False)
    assert len(filters) == 1
