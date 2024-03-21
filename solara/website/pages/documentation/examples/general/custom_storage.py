"""# Custom state storage

Solara makes it easy to store state/data on the server side, scoped to a kernel, using [reactive variables](/api/reactive).

However, sometimes you want to store state yourself in an external system (i.e. not Solara), and for this you can use the
[get_kernel_id()](/api/get_kernel_id) function to get a unique id for each kernel.

If you want to store state/data scoped to a browser session, you can use the [get_session_id()](/api/get_session_id)
function to get a unique id tied to the users browser. This can be used to store state that outlives a page refresh.

In case you want to store state/data scoped to a user, you can use a similar strategy, but use a unique identifier based on the user,
instead of the session id. You can take a look at [Our oauth example](examples/general/login_oauth) or
[the authorization example](/examples/apps/authorization) for inspiration.

"""
from typing import Dict

import solara
import solara.lab

# used only to force updating of the page
force_update_counter = solara.reactive(0)

# Kernel storage is scoped to the kernel, and will be cleared when the kernel is stopped.
kernel_storage: Dict[str, str] = {}


def store_in_kernel_storage(value):
    kernel_storage[solara.get_kernel_id()] = value
    force_update_counter.value += 1


@solara.lab.on_kernel_start
def initialize_kernel_storage():
    # when a kernel gets started, we initialize the dict entry
    kernel_storage[solara.get_kernel_id()] = "This does not"

    def cleanup():
        # when a kernel gets stopped, we remove the dict entry
        del kernel_storage[solara.get_kernel_id()]

    # cleaning up kernel storage, we prevent memory leaks
    return cleanup


# session storage has no lifecycle management, and will only be cleared when the server is restarted.
session_storage: Dict[str, str] = {}


def store_in_session_storage(value):
    session_storage[solara.get_session_id()] = value
    force_update_counter.value += 1


@solara.component
def Page():
    solara.InputText(
        "Stored under the kernel id key",
        value=kernel_storage[solara.get_kernel_id()],
        on_value=store_in_kernel_storage,
        continuous_update=True,
    )

    solara.InputText(
        "Stored under the session id key",
        value=session_storage.get(solara.get_session_id(), "This outlives a page refresh"),
        on_value=store_in_session_storage,
        continuous_update=True,
    )
