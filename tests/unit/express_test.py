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
            solara.express.scatter(df, x="sepal_length", y="sepal_width", size=[10 for ea in df.sepal_length])
        return main

    box, rc = solara.render(Test(), handle_error=False)
    assert set_filter is not None
    set_filter(df["sepal_length"] > 5)
