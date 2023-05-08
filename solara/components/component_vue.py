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

    for name, param in inspect.signature(func).parameters.items():
        if param.default == inspect.Parameter.empty:
            trait = traitlets.Any()
        else:
            trait = traitlets.Any(default_value=param.default)
        traits[name] = trait.tag(sync=True)
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


def _component_vue(vue_path: str, vuetify=True) -> Callable[[Callable[P, None]], Callable[P, solara.Element]]:
    def decorator(func: Callable[P, None]):

        VueWidgetSolaraSub = _widget_vue(vue_path, vuetify=vuetify)(func)

        def wrapper(*args, **kwargs):
            return VueWidgetSolaraSub.element(*args, **kwargs)  # type: ignore

        return wrapper

    return decorator
