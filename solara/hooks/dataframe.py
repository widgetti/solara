import operator
from functools import reduce
from typing import Any, Callable, Dict, List, TypeVar

import react_ipywidgets as react

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
        self.filters: Dict[str, Any] = {}

    def add(self, key, filter):
        self.filters[key] = filter

    def use(self, key):
        # we use this state to trigger update, we could do without
        updater = use_force_update()

        filter, set_filter = react.use_state(self.filters.get(key))

        def on_change():
            set_filter(self.filters.get(key))
            # even if we don't change our own filter, the other may change
            updater()

        def connect():
            self.listeners.append(on_change)

            def cleanup():
                self.listeners.remove(on_change)
                # also remove our filter, and notify the rest
                del self.filters[key]
                for listener in self.listeners:
                    listener()

            return cleanup

        react.use_effect(connect, [key])

        def setter(filter):
            self.filters[key] = filter
            for listener in self.listeners:
                listener()

        otherfilters = [filter for key_other, filter in self.filters.items() if key != key_other]
        return filter, otherfilters, setter


cross_filter_context = react.create_context(CrossFilterStore())


def provide_cross_filter():
    # create it once
    cross_filter_object = react.use_memo(CrossFilterStore, [])
    cross_filter_context.provide(cross_filter_object)


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


def use_cross_filter(name, reducer: Callable[[T, T], T] = operator.and_):
    """Provides cross filtering, all other filters are combined using the reducer.

    Cross filtering will collect a set of filters (from other components), and combine
    them into a single filter, that excludes the filter we set for the current component.
    This is often used in dashboards where a filter is defined in a visualization component,
    but only applied to all other components.
    """
    key = use_unique_key(prefix=f"cross-filter-{name}-")
    print("cf", key)
    cross_filter_store = react.use_context(cross_filter_context)
    _own_filter, otherfilters, set_filter = cross_filter_store.use(key)
    if otherfilters:
        print("otherfilters", otherfilters)
        cross_filter = reduce(reducer, otherfilters[1:], otherfilters[0])
    else:
        cross_filter = None
    return cross_filter, set_filter
