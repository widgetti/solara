import operator
from functools import reduce
from typing import Any, Callable, Dict, List, TypeVar

import solara.util
from solara.hooks.misc import use_force_update, use_unique_key

T = TypeVar("T")

__all__ = [
    "provide_cross_filter",
    "use_cross_filter",
]


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
            # we need to force an extra render after the first render
            # to make sure we have the correct filter, since others components
            # may set a filter after we have rendered, *or* mounted
            on_change()

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


def use_cross_filter(data_key, name: str = "no-name", reducer: Callable[[T, T], T] = operator.and_, eq=solara.util.numpy_equals):
    """Provides cross filtering, all other filters are combined using the reducer.

    Cross filtering will collect a set of filters (from other components), and combine
    them into a single filter, that excludes the filter we set for the current component.
    This is often used in dashboards where a filter is defined in a visualization component,
    but only applied to all other components.

    The graph below shows what happens when component A and B set a filter, and C does not.

    ```mermaid
    graph TD;
        A--"filter A"-->B;
        B--"filter B"-->C;
        A--"filter A"-->C;
        B--"filter B"-->A;
    ```
    """
    key = use_unique_key(prefix=f"cross-filter-{name}-")
    cross_filter_store = solara.use_context(cross_filter_context)
    _own_filter, otherfilters, set_filter = cross_filter_store.use(data_key, key, eq=eq)
    if otherfilters:
        cross_filter = reduce(reducer, otherfilters[1:], otherfilters[0])
    else:
        cross_filter = None
    return cross_filter, set_filter
