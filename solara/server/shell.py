import io
import sys
from binascii import b2a_base64
from threading import local
from unittest.mock import Mock

import reacton.patch_display
from IPython.core.displaypub import DisplayPublisher
from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC
from jupyter_client.session import Session, extract_header
from traitlets import Any, CBytes, Dict, Instance, Type, default


def encode_images(obj):
    # no-op in ipykernel
    return obj


def json_clean(obj):
    # no-op in ipykernel
    return obj


# based on the zmq display publisher from ipykernel
# ideally this goes out of ipykernel
class SolaraDisplayPublisher(DisplayPublisher):
    """A display publisher that publishes data using a ZeroMQ PUB socket."""

    session = Instance(Session, allow_none=True)
    pub_socket = Any(allow_none=True)
    parent_header = Dict({})
    topic = CBytes(b"display_data")

    _thread_local = Any()

    def set_parent(self, parent):
        """Set the parent for outbound messages."""
        self.parent_header = extract_header(parent)

    def _flush_streams(self):
        """flush IO Streams prior to display"""
        sys.stdout.flush()
        sys.stderr.flush()

    @default("_thread_local")
    def _default_thread_local(self):
        """Initialize our thread local storage"""
        return local()

    @property
    def _hooks(self):
        if not hasattr(self._thread_local, "hooks"):
            # create new list for a new thread
            self._thread_local.hooks = []
        return self._thread_local.hooks

    def publish(
        self,
        data,
        metadata=None,
        transient=None,
        update=False,
    ):
        """Publish a display-data message

        Parameters
        ----------
        data : dict
            A mime-bundle dict, keyed by mime-type.
        metadata : dict, optional
            Metadata associated with the data.
        transient : dict, optional, keyword-only
            Transient data that may only be relevant during a live display,
            such as display_id.
            Transient data should not be persisted to documents.
        update : bool, optional, keyword-only
            If True, send an update_display_data message instead of display_data.
        """
        self._flush_streams()
        if metadata is None:
            metadata = {}
        if transient is None:
            transient = {}
        self._validate_data(data, metadata)
        content = {}
        content["data"] = encode_images(data)
        content["metadata"] = metadata
        content["transient"] = transient

        msg_type = "update_display_data" if update else "display_data"

        # Use 2-stage process to send a message,
        # in order to put it through the transform
        # hooks before potentially sending.
        msg = self.session.msg(msg_type, json_clean(content), parent=self.parent_header)

        # Each transform either returns a new
        # message or None. If None is returned,
        # the message has been 'used' and we return.
        for hook in self._hooks:
            msg = hook(msg)
            if msg is None:
                return

        self.session.send(
            self.pub_socket,
            msg,
            ident=self.topic,
        )

    def clear_output(self, wait=False):
        """Clear output associated with the current execution (cell).

        Parameters
        ----------
        wait : bool (default: False)
            If True, the output will not be cleared immediately,
            instead waiting for the next display before clearing.
            This reduces bounce during repeated clear & display loops.

        """
        content = dict(wait=wait)
        self._flush_streams()
        msg = self.session.msg("clear_output", json_clean(content), parent=self.parent_header)
        for hook in self._hooks:
            msg = hook(msg)
            if msg is None:
                return

        self.session.send(
            self.pub_socket,
            msg,
            ident=self.topic,
        )

    def register_hook(self, hook):
        """
        Registers a hook with the thread-local storage.

        Parameters
        ----------
        hook : Any callable object

        Returns
        -------
        Either a publishable message, or `None`.
        The DisplayHook objects must return a message from
        the __call__ method if they still require the
        `session.send` method to be called after transformation.
        Returning `None` will halt that execution path, and
        session.send will not be called.
        """
        self._hooks.append(hook)

    def unregister_hook(self, hook):
        """
        Un-registers a hook with the thread-local storage.

        Parameters
        ----------
        hook : Any callable object which has previously been
            registered as a hook.

        Returns
        -------
        bool - `True` if the hook was removed, `False` if it wasn't
            found.
        """
        try:
            self._hooks.remove(hook)
            return True
        except ValueError:
            return False


class SolaraInteractiveShell(InteractiveShell):
    display_pub_class = Type(SolaraDisplayPublisher)
    history_manager = Any()  # type: ignore

    def set_parent(self, parent):
        """Tell the children about the parent message."""
        self.display_pub.set_parent(parent)

    def init_history(self):
        self.history_manager = Mock()  # type: ignore

    def init_display_formatter(self):
        super().init_display_formatter()
        assert self.display_formatter is not None
        self.display_formatter.ipython_display_formatter = reacton.patch_display.ReactonDisplayFormatter()

        # matplotlib support for display(figure)
        # IPython.core.pylabtools has support for this, but it requires importing matplotlib
        # which would slow down startup, so we do it here using for_type using a string as argument.
        def encode_png(figure, **kwargs):
            f = io.BytesIO()
            format = "png"
            figure.savefig(f, format=format, **kwargs)
            bytes_data = f.getvalue()
            base64_data = b2a_base64(bytes_data, newline=False).decode("ascii")
            return base64_data

        formatter = self.display_formatter.formatters["image/png"]
        formatter.for_type("matplotlib.figure.Figure", encode_png)

    def init_display_pub(self):
        super().init_display_pub()
        self.display_pub.register_hook(self.display_in_reacton_hook)

    def display_in_reacton_hook(self, msg):
        """Will intercept a display call and add the display data to an output widget when in a reacton context/render function."""
        # similar to reacton.patch_display.publish
        from reacton.core import get_render_context

        rc = get_render_context(required=False)
        # only during the render phase we want to capture the display calls
        # during the reconsolidation phase we want to let the original display publisher do its thing
        # such as adding it to a output widget
        if rc is not None and not rc.reconsolidating and msg["msg_type"] == "display_data":
            from reacton.ipywidgets import Output

            Output(outputs=[{"output_type": "display_data", "data": msg["content"]["data"], "metadata": msg["content"]["metadata"]}])
            return None  # do not send to the frontend
        return msg

    def reset(self, new_session=True, aggressive=False):
        # if we dont override this with a dummy, the unittests will take a long time
        # to exit. Hitting ctrl-c showed the following stacktrace:
        # Traceback (most recent call last):
        # File "/Users/maartenbreddels/miniconda3/envs/dev/lib/python3.9/site-packages/IPython/core/interactiveshell.py", line 3924, in atexit_operations
        #     self.reset(new_session=False)
        # File "/Users/maartenbreddels/miniconda3/envs/dev/lib/python3.9/site-packages/IPython/core/interactiveshell.py", line 1456, in reset
        #     self.displayhook.flush()
        # File "/Users/maartenbreddels/miniconda3/envs/dev/lib/python3.9/site-packages/IPython/core/displayhook.py", line 311, in flush
        #     gc.collect()
        # So this dummy will prevent that.
        pass


InteractiveShellABC.register(SolaraInteractiveShell)
