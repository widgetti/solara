from ..utils.dataframe import df_type


def use_df_column_names(df):
    if df_type(df) == "vaex":
        return df.get_column_names()
    elif df_type(df) == "pandas":
        return df.columns.tolist()
    elif df_type(df) == "polars":
        return df.columns
    else:
        raise TypeError(f"{type(df)} not supported")
