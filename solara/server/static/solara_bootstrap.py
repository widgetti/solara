import sys

import micropip
import micropip._micropip
import micropip.package
import solara_bootstrap


class IOLoop:
    pass


class ZMQStream:
    pass


class MessageTracker:
    pass


class Context:
    pass


class Socket:
    pass


class Message:
    pass


NOBLOCK = 1
REQ = None
DEALER = 2
SUB = 3
POLLOUT = 4

sugar = solara_bootstrap
socket = solara_bootstrap
asyncio = solara_bootstrap
core = solara_bootstrap
error = solara_bootstrap
ioloop = solara_bootstrap


class ProfileDir:
    pass


class StdinNotImplementedError(Exception):
    pass


class Queue:
    pass


class QueueEmpty:
    pass


class InteractiveShell:
    pass


def display(*args, **kwargs):
    raise NotImplementedError


def clear_output(*args, **kwargs):
    raise NotImplementedError


def get_ipython():
    return None


class Process:
    pass


async def main():
    # fake some packages we don't need
    micropip.install("numpy")
    micropip._micropip.PACKAGE_MANAGER.installed_packages["debugpy"] = micropip.package.PackageMetadata(name="debugpy", version="1.6", source="")
    micropip._micropip.PACKAGE_MANAGER.installed_packages["notebook"] = micropip.package.PackageMetadata(name="notebook", version="6.5", source="")
    micropip._micropip.PACKAGE_MANAGER.installed_packages["pyzmq"] = micropip.package.PackageMetadata(name="pyzmq", version="23.0", source="")
    micropip._micropip.PACKAGE_MANAGER.installed_packages["psutil"] = micropip.package.PackageMetadata(name="psutil", version="22.3", source="")
    micropip._micropip.PACKAGE_MANAGER.installed_packages["tornado"] = micropip.package.PackageMetadata(name="tornado", version="6.2", source="")
    micropip._micropip.PACKAGE_MANAGER.installed_packages["argon2-cffi-bindings"] = micropip.package.PackageMetadata(
        name="argon2-cffi-bindings", version="22.3", source=""
    )
    micropip._micropip.PACKAGE_MANAGER.installed_packages["ipython"] = micropip.package.PackageMetadata(name="ipython", version="8.3", source="")
    micropip._micropip.PACKAGE_MANAGER.installed_packages["jupyter_client"] = micropip.package.PackageMetadata(name="jupyter_client", version="7.3", source="")

    sys.modules["zmq"] = solara_bootstrap
    sys.modules["zmq.asyncio"] = solara_bootstrap
    sys.modules["zmq.eventloop"] = solara_bootstrap
    sys.modules["zmq.eventloop.ioloop"] = solara_bootstrap
    sys.modules["zmq.eventloop.zmqstream"] = solara_bootstrap

    for fake in (
        "psutil IPython IPython.core IPython.core.interactiveshell IPython.core.getipython IPython.core.error "
        "IPython.core.profiledir IPython.display tornado tornado.ioloop tornado.queues".split()
    ):
        sys.modules[fake] = solara_bootstrap

    requirements = [
        "Pygments==2.13.0",
        "ipywidgets<8",
        "pydantic",
        "jinja2",
        "bqplot",
        "altair",
        "vega_datasets",
        "plotly",
        "ipycanvas",
    ]
    for dep in requirements:
        await micropip.install(dep, keep_going=True)
    await micropip.install("/wheels/solara-0.13.0-py2.py3-none-any.whl", keep_going=True)
    import solara

    el = solara.Warning(text="lala")
    import solara

    solara.render_fixed(el)
    return el
