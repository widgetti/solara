import pytest
import solara
import vaex
import polars as pl
from solara.components.datatable import DataTable, DataTableWidget

df_vaex = vaex.datasets.titanic()
df_pandas = df_vaex.to_pandas_df()
df_polars = pl.from_pandas(df_pandas)


@pytest.mark.parametrize("df", [df_vaex, df_pandas, df_polars])
def test_render(df):
    @solara.component
    def Test():
        return DataTable(df)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert isinstance(widget, DataTableWidget)
    assert len(widget.items) == 20
