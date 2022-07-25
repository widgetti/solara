import time

from ipyvue import VueWidget


def repeat_while_false(f, timeout=1):
    while True:
        result = f()
        if result:
            return
        if timeout is not None:
            if timeout <= 0:
                raise TimeoutError("Timeout")
            timeout -= 0.1
            time.sleep(0.1)
        else:
            time.sleep(0.1)


def repeat_while_true(f, timeout=1):
    repeat_while_false(lambda: not f(), timeout)


def event_and_mods(widget: VueWidget, event):
    event_match = [k for k in widget._event_handlers_map.keys() if k.startswith(event)]
    if event_match:
        return event_match[0]
    raise ValueError(f"'{event}' not found in widget {widget}")


def fire(widget: VueWidget, event):
    event_name = event_and_mods(widget, event)
    # manually call, because the CallbackDispatcher will eat exceptions
    for callback in widget._event_handlers_map[event_name].callbacks:
        callback(widget, event_name, {})


def click(widget: VueWidget, event="click"):
    fire(widget, "click")
