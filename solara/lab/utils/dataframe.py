from typing import List, Union


def get_pandas_major():
    import pandas as pd

    return int(pd.__version__[0])


def df_type(df):
    return df.__class__.__module__.split(".")[0]


def df_len(df) -> int:
    """Return the number of rows in a dataframe."""
    return len(df)


def df_columns(df) -> List[str]:
    """Return a list of column names from a dataframe."""
    if df_type(df) == "vaex":
        return df.get_column_names()
    elif df_type(df) == "pandas":
        return df.columns.tolist()
    elif df_type(df) == "polars":
        return df.columns
    else:
        raise TypeError(f"{type(df)} not supported")


def df_row_names(df) -> List[Union[int, str]]:
    """Return a list of row names from a dataframe."""
    if df_type(df) == "vaex" or df_type(df) == "polars":
        return list(range(df_len(df)))
    elif df_type(df) == "pandas":
        return df.index.tolist()
    else:
        raise TypeError(f"{type(df)} not supported")


def df_slice(df, start: int, stop: int):
    """Return a subset of rows from a dataframe."""
    if df_type(df) == "pandas":
        return df.iloc[start:stop]
    else:
        return df[start:stop]


def df_records(df) -> List[dict]:
    """A list of records from a dataframe."""
    if df_type(df) == "pandas":
        return df.to_dict("records")
    elif df_type(df) == "polars":
        return df.to_dicts()
    elif df_type(df) == "vaex":
        return df.to_records()
    else:
        raise TypeError(f"{type(df)} not supported")


def df_unique(df, column, limit=None):
    if df_type(df) == "vaex":
        return df.unique(column, limit=limit + 1 if limit else None, limit_raise=False)
    if df_type(df) == "pandas":
        x = df[column].unique()  # .to_numpy()
        return x[:limit]
    else:
        raise TypeError(f"{type(df)} not supported")


def df_value_count(df, column, limit=None):
    if df_type(df) == "vaex":
        dfv = df.groupby(column, agg="count", sort="count", ascending=False)
        dfv = dfv.to_pandas_df().rename({column: "value"}, axis=1)
        return dfv[:limit]
    if df_type(df) == "pandas":
        dfv = df[column].value_counts(dropna=False).to_frame()
        dfv = dfv.reset_index()
        if get_pandas_major() >= 2:
            dfv = dfv.rename({column: "value"}, axis=1)
        else:
            dfv = dfv.rename({"index": "value", column: "count"}, axis=1)
        return dfv[:limit]
    else:
        raise TypeError(f"{type(df)} not supported")


def df_range(df, column):
    if df_type(df) == "vaex":
        minmax = df[column].minmax()
        return minmax[0].item(), minmax[1].item()
    if df_type(df) == "pandas":
        return df[column].min().item(), df[column].max().item()
    else:
        raise TypeError(f"{type(df)} not supported")


def df_filter_missing(df, column):
    if df_type(df) == "vaex":
        return df[column].isna()
    if df_type(df) == "pandas":
        return df[column].isna()
    else:
        raise TypeError(f"{type(df)} not supported")


def df_filter_values(df, column, values, invert=False):
    if df_type(df) == "vaex":
        filter = df[column].isin(values)
        if invert:
            filter = ~filter
        return filter
    if df_type(df) == "pandas":
        filter = df[column].isin(values)
        if invert:
            filter = ~filter
        return filter
    else:
        raise TypeError(f"{type(df)} not supported")


def df_py_types(df):
    """Return a dict with column names as keys and python types as values.

    Support types are
        * int
        * float
        * str
        * bool

    If a type is not supported, the internal type is returned.

    """
    import numpy as np

    if df_type(df) == "vaex":
        schema = df.schema()
        py_types = [int, float, str, bool]

        def py_type(dtype):
            for k in py_types:
                if dtype == k:
                    return k
            return dtype

        return {name: py_type(dtype) for name, dtype in schema.items()}
    elif df_type(df) == "pandas":
        schema = df.dtypes

        def py_type(dtype):
            if isinstance(dtype, np.dtype):
                if dtype.kind in "iu":
                    return int
                elif dtype.kind == "f":
                    return float
                elif dtype.kind == "b":
                    return bool
                else:
                    return dtype
            else:
                return dtype

        return {name: py_type(dtype) for name, dtype in schema.items()}
    else:
        raise TypeError(f"{type(df)} not supported")
