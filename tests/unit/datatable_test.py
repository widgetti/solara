from pathlib import Path
import pytest
import solara

try:
    import vaex
except ImportError:
    vaex = None
import polars as pl
import pandas as pd

from solara.components.datatable import DataTable, DataTableWidget


HERE = Path(__file__).parent

titanic_url = HERE.parent / "titanic.csv"
df_pandas = pd.read_csv(titanic_url)
# convert columns to numpy-backed types for polars conversion without pyarrow
# df_pandas.index = df_pandas.index.astype('int64')
for col in df_pandas.columns:
    # Check specifically for pandas nullable dtypes, checking for attribute existence for compatibility
    if hasattr(pd, "Int64Dtype") and isinstance(df_pandas[col].dtype, pd.Int64Dtype):
        # Fill NaN and convert to numpy's int64
        df_pandas[col] = df_pandas[col].fillna(0).astype("int64")
    elif hasattr(pd, "Float64Dtype") and isinstance(df_pandas[col].dtype, pd.Float64Dtype):
        # Fill NaN and convert to numpy's float64
        df_pandas[col] = df_pandas[col].fillna(0.0).astype("float64")
    elif df_pandas[col].dtype == "object":
        # Try converting object columns to string
        try:
            df_pandas[col] = df_pandas[col].astype(str)
            # You might need more specific NaN handling here depending on the column
            # For now, converting NaN to the string 'nan'
            df_pandas[col] = df_pandas[col].fillna("nan")
        except Exception as e:
            print(f"Could not convert object column {col} to string: {e}")
            # Handle specific conversion errors if necessary

if vaex is not None:
    df_vaex = vaex.from_pandas(df_pandas)
df_polars = pl.from_pandas(df_pandas)


@pytest.mark.parametrize("df", [df_vaex, df_pandas, df_polars] if vaex is not None else [df_pandas, df_polars])
def test_render(df):
    @solara.component
    def Test():
        return DataTable(df)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert isinstance(widget, DataTableWidget)
    assert len(widget.items) == 20
