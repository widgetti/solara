import operator
from functools import reduce
from typing import Any, Callable, Dict, List, TypeVar

import solara.util
from solara.hooks.misc import use_force_update, use_unique_key

max_unique = 100
T = TypeVar("T")

__all__ = [
    "df_type",
    "df_unique",
    "provide_cross_filter",
    "use_cross_filter",
    "use_df_column_names",
    "max_unique",
]


def df_type(df):
    return df.__class__.__module__.split(".")[0]


class CrossFilterStore:
    def __init__(self) -> None:
        self.listeners: List[Callable] = []
        self.filters: Dict[Any, Dict[str, Any]] = {}

    def add(self, data_key, key, filter):
        data_filters = self.filters.setdefault(data_key, {})
        data_filters[key] = filter

    def use(self, data_key, key, eq=None):
        # we use this state to trigger update, we could do without
        updater = use_force_update()

        data_filters = self.filters.setdefault(data_key, {})
        filter, set_filter = solara.use_state(data_filters.get(key), eq=eq)

        def on_change():
            set_filter(data_filters.get(key))
            # even if we don't change our own filter, the other may change
            updater()

        def connect():
            self.listeners.append(on_change)

            def cleanup():
                self.listeners.remove(on_change)
                # also remove our filter, and notify the rest
                data_filters.pop(key, None)  # remove, ignoring key error
                for listener in self.listeners:
                    listener()

            return cleanup

        solara.use_effect(connect, [key])

        def setter(filter):
            data_filters[key] = filter
            for listener in self.listeners:
                listener()

        otherfilters = [filter for key_other, filter in data_filters.items() if key != key_other and filter is not None]
        return filter, otherfilters, setter


cross_filter_context = solara.create_context(CrossFilterStore())


def provide_cross_filter():
    # create it once
    cross_filter_object = solara.use_memo(CrossFilterStore, [])
    cross_filter_context.provide(cross_filter_object)
    return cross_filter_object


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


def use_cross_filter(data_key, name: str = "no-name", reducer: Callable[[T, T], T] = operator.and_, eq=solara.util.numpy_equals):
    """Provides cross filtering, all other filters are combined using the reducer.

    Cross filtering will collect a set of filters (from other components), and combine
    them into a single filter, that excludes the filter we set for the current component.
    This is often used in dashboards where a filter is defined in a visualization component,
    but only applied to all other components.
    """
    key = use_unique_key(prefix=f"cross-filter-{name}-")
    cross_filter_store = solara.use_context(cross_filter_context)
    _own_filter, otherfilters, set_filter = cross_filter_store.use(data_key, key, eq=eq)
    if otherfilters:
        cross_filter = reduce(reducer, otherfilters[1:], otherfilters[0])
    else:
        cross_filter = None
    return cross_filter, set_filter
