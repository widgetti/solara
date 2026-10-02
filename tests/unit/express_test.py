import plotly.express as px

import solara
import solara.express

df = px.data.iris()


def test_cross_filter():
    filter, set_filter = None, None

    @solara.component
    def Test():
        nonlocal filter, set_filter
        solara.provide_cross_filter()
        filter, set_filter = solara.use_cross_filter(id(df))

        with solara.HBox() as main:
            solara.express.scatter(df, x="sepal_length", y="sepal_width")
            solara.express.scatter(df, x="sepal_length", y="sepal_width", size=[10 for ea in df.sepal_length], log_x=True)
        return main

    box, rc = solara.render(Test(), handle_error=False)
    assert set_filter is not None
    set_filter(df["sepal_length"] > 5)


def test_histogram():
    # our copy of px.histogram passes all its arguments to plotly, which should accept them (e.g. subtitle in plotly 6)
    fig = solara.express.histogram(df, "species", title="title")
    box, rc = solara.render(fig, handle_error=False)
    rc.close()
