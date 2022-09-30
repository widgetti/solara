"""

Wraps plotly express function and adds cross filtering support.

Instead of `plotly.express' you can use `solara.express` instead.

```python
# import plotly.express as px
import solara.express as px

df = px.data.iris()
px.histogram(df, "species")
px.scatter(df, x="sepal_width", y="sepal_length", color="species")
```


Click the lasso icon in the top scatter plot to select points, which should then be filtered out in the other
plots.


"""

import plotly.express as px
import solara
import solara.express as spx

df = px.data.iris()


@solara.component
def Page():
    solara.provide_cross_filter()
    fig = px.histogram(df, "species")
    fig.update_layout(dragmode="select", selectdirection="h")

    with solara.VBox() as main:
        spx.scatter(df, x="sepal_width", y="sepal_length", color="species")
        spx.scatter_3d(df, x="sepal_width", y="sepal_length", z="petal_width")
        spx.FigurePlotlyCrossFiltered(fig)
    return main
