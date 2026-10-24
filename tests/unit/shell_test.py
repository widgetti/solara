from unittest.mock import Mock

import IPython.display

from solara.server import kernel, kernel_context


def test_shell(no_kernel_context):
    ws1 = Mock()
    ws2 = Mock()
    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    kernel1.session.websockets.add(ws1)
    kernel2.session.websockets.add(ws2)
    context1 = kernel_context.VirtualKernelContext(id="1", kernel=kernel1, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="2", kernel=kernel2, session_id="session-2")

    with context1:
        IPython.display.display("test1")
        assert ws1.send.call_count == 1
        assert ws2.send.call_count == 0
    with context2:
        IPython.display.display("test1")
        assert ws1.send.call_count == 1
        assert ws2.send.call_count == 1

    assert kernel1.shell is not None
    magics_manager = kernel1.shell.magics_manager
    assert magics_manager is not None
    registry = magics_manager.registry
    # IPython 9 loads magics lazily (registry is a _MagicsRegistry); older versions
    # create ScriptMagics with the shell, so there is nothing to skip there.
    if type(registry).__name__ == "_MagicsRegistry":
        # a new session should not pay for ScriptMagics (see SolaraInteractiveShell.__init__)
        assert "ScriptMagics" not in dict.keys(registry)
