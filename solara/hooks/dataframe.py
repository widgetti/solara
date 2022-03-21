import operator
from functools import reduce
from typing import Any, Dict, Optional, cast

import numpy as np
import react_ipywidgets as react

max_unique = 100


def df_type(df):
    return df.__class__.__module__.split(".")[0]


def provide_crossfilter(key: str = "crossfilter"):
    crossfilter: Dict[str, Any]
    crossfilter, set_crossfilter = react.use_state(cast(Dict[str, Any], {}))
    react.provide_context(key, [crossfilter, set_crossfilter])


def df_unique(df, column, limit=None):
    if df_type(df) == "vaex":
        return df.unique(column, limit=max_unique + 1, limit_raise=False)
    if df_type(df) == "pandas":
        x = df[column].unique()  # .to_numpy()
        return x[:limit]
    else:
        raise TypeError(f"{type(df)} not supported")


def use_df_column_names(df):
    if df_type(df) == "vaex":
        return df.get_column_names()
    elif df_type(df) == "pandas":
        return df.columns.tolist()
    else:
        raise TypeError(f"{type(df)} not supported")


def use_cross_filter(filter_key: Optional[str], key: str = "crossfilter"):
    crossfilter: Dict[str, Any]
    crossfilter, set_crossfilter = react.use_context(key)

    def set_filter(filter):
        crossfilter_copy = crossfilter.copy()
        if filter_key:
            crossfilter_copy[filter_key] = filter
            set_crossfilter(crossfilter_copy)

    otherfilters = [v for k, v in crossfilter.items() if k != filter_key and v is not None]
    # def filter(df):
    if 1:
        if otherfilters:
            #             otherfilters_expressions = [df[k] for k in otherfilters]
            filter = reduce(operator.and_, otherfilters[1:], otherfilters[0])
        #             print(filter)
        # turn filter
        else:
            filter = None
            # return None
    return filter, set_filter


def use_df_pivot_data(df, x, y, agg):
    agg_name = str(agg)
    data = {
        "x": x,
        "y": y,
        "agg": agg_name,
        "values": None,
        "values_x": None,
        "values_y": None,
        "headers": {"x": [], "y": []},
        "counts": {"x": 0, "y": 0},
    }

    columns = [*data["x"], *data["y"]]
    agg_column = "agg_count__"
    row_index = "__row_index__"

    def df_groupby_agg(df, columns, aggregate):
        if df_type(df) == "pandas":
            gb = df.groupby(columns, as_index=False)
            aggs = {agg_column: (columns[0], "size")}
            print(columns, aggs)
            return gb.agg(**aggs)
        elif df_type(df) == "vaex":
            return df.groupby(columns, sort=True).agg({agg_column: agg})
        else:
            raise TypeError(f"{type(df)} not supported")

    if data["x"] and data["y"]:
        dfg = df_groupby_agg(df, columns, agg)
    #         print(dfg)
    if data["x"]:
        dfgx = df_groupby_agg(df, data["x"], agg)
        #         dfgx = df.groupby(data['x'], sort=True).agg({agg_column: agg})
        dfgx[row_index] = np.arange(len(dfgx), dtype="int64")
    #         print('x', dfgx)
    #         print(dfgx[agg_column].tolist())
    #         dfgx[row_index] = vaex.vrange(0, len(dfgx), dtype='int64')
    if data["y"]:
        dfgy = df_groupby_agg(df, data["y"], agg)
        #         dfgx = df.groupby(data['x'], sort=True).agg({agg_column: agg})
        dfgy[row_index] = np.arange(len(dfgy), dtype="int64")
    #         print('y', dfgy)
    #         dfgx[row_index] = vaex.vrange(0, len(dfgx), dtype='int64')
    #         dfgy = df.groupby(data['y'], sort=True).agg({agg_column: agg})
    #         dfgy[row_index] = vaex.vrange(0, len(dfgy), dtype='int64')

    if df_type(df) == "pandas":
        #         dfg_total = df.agg(agg)
        dfg_total = df.agg(**{agg_column: (columns[0], "size")}).to_numpy()[0][0]
    elif df_type(df) == "vaex":
        # agg = vaex.agg.count()
        dfg_total = df._agg(agg)
    else:
        raise TypeError(f"{type(df)} not supported")

    def formatter(value):
        if isinstance(value, float):
            return f"{value:,.2f}"
        else:
            return f"{value:,d}"

    if data["x"] and data["y"]:
        data["values"] = [[None] * len(dfgy) for _ in range(len(dfgx))]
    if data["x"]:
        #         print(dfgx[agg_column].tolist())
        data["values_x"] = list(map(formatter, dfgx[agg_column].tolist()))
    if data["y"]:
        data["values_y"] = list(map(formatter, dfgy[agg_column].tolist()))
    data["total"] = formatter(dfg_total)
    #     print(data)

    if data["x"] and data["y"]:
        for row in dfg.to_records():
            dfs = {"x": dfgx, "y": dfgy}
            for column in columns:
                axis_name = "x" if column in data["x"] else "y"
                df_axis = dfs[axis_name]
                #                 print("before", df_axis)
                if row[column] is None:
                    df_axis = df_axis[df[column].ismissing()]
                else:
                    df_axis = df_axis[df_axis[column] == row[column]]
                #                 print("after", df_axis, column, row[column])
                dfs[axis_name] = df_axis
            assert len(dfs["x"])
            assert len(dfs["y"])
            xi = dfs["x"][row_index].tolist()[0]
            yi = dfs["y"][row_index].tolist()[0]
            value = row[agg_column]
            data["values"][xi][yi] = formatter(value)

    if data["x"]:
        data["headers"]["x"] = [dfgx[k].tolist() for k in data["x"]]
        data["counts"]["x"] = len(dfgx)
    if data["y"]:
        data["headers"]["y"] = [dfgy[k].tolist() for k in data["y"]]
        data["counts"]["y"] = len(dfgy)

    return data
