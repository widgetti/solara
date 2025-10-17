import inspect
import os
from typing import Any, Callable, Dict, Type

import ipyvue as vue
import ipyvuetify as v
import ipywidgets as widgets
import traitlets
import typing_extensions

import solara

P = typing_extensions.ParamSpec("P")

default_to_json = widgets.widget_serialization["to_json"]
default_from_json = widgets.widget_serialization["from_json"]


def _widget_from_signature(
    classname,
    base_class: Type[widgets.Widget],
    func: Callable[..., None],
    event_prefix: str,
    tags: Dict[str, Any],
    to_json: Dict[str, Callable[[Any, widgets.Widget], Any]],
    from_json: Dict[str, Callable[[Any, widgets.Widget], Any]],
) -> Type[widgets.Widget]:
    classprops: Dict[str, Any] = {}

    parameters = inspect.signature(func).parameters
    for name, param in parameters.items():
        if name.startswith("event_"):
            event_name = name[6:]
            event_name_full = name  # LLM's are quick stubborn in wanting to call `event_foo` instead of `foo`

            def event_handler(self, data, buffers=None, event_name=event_name, param=param):
                callback = self._event_callbacks.get(event_name, param.default)
                if not callback:
                    # support 'event_foo'
                    callback = self._event_callbacks.get(event_name_full, None)
                if callback:
                    if buffers:
                        callback(data, buffers)
                    else:
                        callback(data)

            classprops[f"vue_{event_name}"] = event_handler
            classprops[f"vue_{event_name_full}"] = event_handler
        elif name.startswith("on_") and name[3:] in parameters:
            # callback, will be handled by reacton
            continue
        else:
            if param.default == inspect.Parameter.empty:
                trait = traitlets.Any()
            else:
                trait = traitlets.Any(default_value=param.default)
            tag = dict(sync=True, to_json=to_json.get(name, default_to_json), from_json=from_json.get(name, default_from_json))
            tag.update(**tags.get(name, {}))
            classprops[name] = trait.tag(**tag)
    # maps event_foo to a callable
    classprops["_event_callbacks"] = traitlets.Dict(default_value={})

    widget_class = type(classname, (base_class,), classprops)
    return widget_class


def _widget_vue(
    vue_path: str,
    vuetify=True,
    to_json: Dict[str, Callable[[Any, widgets.Widget], Any]] = {},
    from_json: Dict[str, Callable[[Any, widgets.Widget], Any]] = {},
    tags: Dict[str, Any] = {},
) -> Callable[[Callable[P, None]], Type[v.VuetifyTemplate]]:
    def decorator(func: Callable[P, None]):
        class VuetifyWidgetSolara(v.VuetifyTemplate):
            template_file = (os.path.abspath(inspect.getfile(func)), vue_path)

        class VueWidgetSolara(vue.VueTemplate):
            template_file = (os.path.abspath(inspect.getfile(func)), vue_path)

        base_class = VuetifyWidgetSolara if vuetify else VueWidgetSolara
        widget_class = _widget_from_signature("VueWidgetSolaraSub", base_class, func, "vue_", to_json=to_json, from_json=from_json, tags=tags)

        return widget_class

    return decorator


def component_vue(
    vue_path: str,
    vuetify=True,
    tags: Dict[str, Any] = {},
    to_json: Dict[str, Callable[[Any, widgets.Widget], Any]] = {},
    from_json: Dict[str, Callable[[Any, widgets.Widget], Any]] = {},
) -> Callable[[Callable[P, None]], Callable[P, solara.Element]]:
    """Decorator to create a component backed by a Vue template.

    Although many components can be made from the Python side, sometimes it is easier to write components using Vue directly.
    It can also be beneficial for performance, since instead of creating many widgets from the Python side we only send data to
    the frontend. If event handling is also done on the frontend, this reduces latency and makes you app feel much smoother.


    All arguments of the function are exposed as Vue properties. Argument pairs of the form `foo`, and `on_foo`
    are assumed by refer to the same vue property, with `on_foo` being the event handler when `foo` changes from
    the vue template.

    Arguments of the form `event_foo` should be callbacks that can be called from the vue template. They are
    available as the function `foo` and `event_foo` in the vue template.

    Note that `foo` was kept for backwards compatibility, but LLM's have a tendency to use `event_foo`, so this was
    changed to `event_foo`.

    [See the vue v2 api](https://v2.vuejs.org/v2/api/) for more information on how to use Vue, like `watch`,
    `methods` and lifecycle hooks such as `mounted` and `destroyed`.

    See the [Vue component example](/documentation/examples/general/vue_component) for an example of how to use this decorator.

    The underlying trait can be passed extra arguments by passing a dictionary to the `tags` argument.
    The most common case is to pass a custom serializer and deserializer for the trait, for which we added the
    strictly typed `to_json` and `from_json` arguments.
    Otherwise pass a dictionary to the `tags` argument, see the example below for more details.


    ## Examples

    A component that takes a `foo` argument and an `on_foo` callback that gets called when `foo` changes (from the frontend).

    ```python
    import solara

    @solara.component_vue("my_foo_component.vue")
    def MyFooComponent(foo: int, on_foo: Callable[[int], None]):
        pass
    ```

    The following component only takes in a month argument and an event_date_clicked callback that gets called from
    the vue template using `this.date_clicked({'extra-data': 42, 'day': this.day})`.
    ```python
    import solara

    @solara.component_vue("my_date_component.vue")
    def MyDateComponent(month: int, event_date_clicked: Callable):
        pass
    ```

    ## Example with custom serializer and deserializer

    ```python
    import solara

    def to_json_datetime(value: datetime.date, widget: widgets.Widget) -> str:
        return value.isoformat()

    def from_json_datetime(value: str, widget: widgets.Widget) -> datetime.date:
        return datetime.date.fromisoformat(value)

    @solara.component_vue("my_date_component.vue", to_json={"month": to_json_datetime}, from_json={"month": from_json_datetime})
    def MyDateComponent(month: datetime.date, event_date_clicked: Callable):
        pass

    # the following will be the same, except that it is less strictly typed
    @solara.component_vue("my_date_component.vue", tags={"month": {"to_json": to_json_datetime, "from_json": from_json_datetime}})
    def MyDateComponentSame(month: datetime.date, event_date_clicked: Callable):
        pass

    ```

    ## Arguments

     * `vue_path`: The path to the Vue template file.
     * `vuetify`: Whether the Vue template uses Vuetify components.

    """

    def decorator(func: Callable[P, None]):
        VueWidgetSolaraSub = _widget_vue(vue_path, vuetify=vuetify, to_json=to_json, from_json=from_json, tags=tags)(func)

        def wrapper(*args, **kwargs):
            event_callbacks = {}
            kwargs = kwargs.copy()
            # take out all events named like event_foo and put them in a separate dict
            for name in list(kwargs):
                if name.startswith("event_"):
                    event_callbacks[name[6:]] = kwargs.pop(name)
            if event_callbacks:
                kwargs["_event_callbacks"] = event_callbacks
            return VueWidgetSolaraSub.element(*args, **kwargs)  # type: ignore

        return wrapper

    return decorator


_component_vue = component_vue
