import pytest
import solara
import vaex
from solara.components.datatable import DataTable, DataTableWidget

df_vaex = vaex.datasets.titanic()
df_pandas = df_vaex.to_pandas_df()


@pytest.mark.parametrize("df", [df_vaex, df_pandas])
def test_render(df):
    @solara.component
    def Test():
        return DataTable(df)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert isinstance(widget, DataTableWidget)
    assert len(widget.items) == 20
