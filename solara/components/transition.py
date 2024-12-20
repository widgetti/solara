import solara
from .component_vue import component_vue


@solara.component
def Transition(show_first=True, children=[], name="", mode="", duration=0.2):
    """Transitions between two child elements with an animation.

    These transitions are based on Vue's transition system.

    * https://v2.vuejs.org/v2/guide/transitions
    * https://vuejs.org/guide/built-ins/transition

    """
    # in Python land we like to work with seconds
    return _Transition(show_first=show_first, children=children, name=name, mode=mode, duration=duration * 1000)


@component_vue("transition.vue")
def _Transition(show_first=True, children=[], name="", mode="", duration=200):
    pass  # just a dummy function
