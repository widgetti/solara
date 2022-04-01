import pytest
import vaex

from solara.kitchensink import react

from .datatable import DataTable, DataTableWidget

df_vaex = vaex.datasets.titanic()
df_pandas = df_vaex.to_pandas_df()


@pytest.mark.parametrize("df", [df_vaex, df_pandas])
def test_render(df):
    @react.component
    def Test():
        return DataTable(df)

    widget, rc = react.render_fixed(Test(), handle_error=False)
    assert isinstance(widget, DataTableWidget)
    assert len(widget.items) == 20
