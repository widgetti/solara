import inspect
from typing import Callable, Type

import ipyvue as vue
import ipyvuetify as v
import ipywidgets as widgets
import traitlets
import typing_extensions

import solara

P = typing_extensions.ParamSpec("P")


def _widget_from_signature(name, base_class: Type[widgets.Widget], func: Callable[..., None]) -> Type[widgets.Widget]:
    traits = {}

    parameters = inspect.signature(func).parameters
    for name, param in parameters.items():
        if name.startswith("on_") and name[3:] in parameters:
            # callback, will be handled by reacton
            continue
        if param.default == inspect.Parameter.empty:
            trait = traitlets.Any()
        else:
            trait = traitlets.Any(default_value=param.default)
        traits[name] = trait.tag(sync=True, **widgets.widget_serialization)
    widget_class = type(name, (base_class,), traits)
    return widget_class


def _widget_vue(vue_path: str, vuetify=True) -> Callable[[Callable[P, None]], Type[v.VuetifyTemplate]]:
    def decorator(func: Callable[P, None]):
        class VuetifyWidgetSolara(v.VuetifyTemplate):
            template_file = (inspect.getfile(func), vue_path)

        class VueWidgetSolara(vue.VueTemplate):
            template_file = (inspect.getfile(func), vue_path)

        base_class = VuetifyWidgetSolara if vuetify else VueWidgetSolara
        widget_class = _widget_from_signature("VueWidgetSolaraSub", base_class, func)

        return widget_class

    return decorator


def component_vue(vue_path: str, vuetify=True) -> Callable[[Callable[P, None]], Callable[P, solara.Element]]:
    """Decorator to create a component backed by a Vue template.

    Although many components can be made from the Python side, sometimes it is easier to write components using Vue directly.
    It can also be beneficial for performance, since instead of creating many widgets from the Python side we only send data to
    the frontend. If event handling is also done on the frontend, this reduces latency and makes you app feel much smoother.


    All arguments of the function are exposed as Vue properties. Argument pairs of the form `foo`, and `on_foo`
    are assumed by refer to the same vue property, with `on_foo` being the event handler when `foo` changes from
    the vue template.

    [See the vue v2 api](https://v2.vuejs.org/v2/api/) for more information on how to use Vue, like `watch`,
    `methods` and lifecycle hooks such as `mounted` and `destroyed`.

    See the [Vue component example](/examples/general/vue_component) for an example of how to use this decorator.

    ## Arguments

     * `vue_path`: The path to the Vue template file.
     * `vuetify`: Whether the Vue template uses Vuetify components.

    """

    def decorator(func: Callable[P, None]):
        VueWidgetSolaraSub = _widget_vue(vue_path, vuetify=vuetify)(func)

        def wrapper(*args, **kwargs):
            return VueWidgetSolaraSub.element(*args, **kwargs)  # type: ignore

        return wrapper

    return decorator


_component_vue = component_vue
