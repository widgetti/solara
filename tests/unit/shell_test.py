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


def test_shell_history_manager_makes_no_cyclic_garbage():
    import gc

    from solara.server.shell import NoHistoryManager, SolaraInteractiveShell

    shell = SolaraInteractiveShell()
    history_manager = shell.history_manager  # type: ignore[has-type]
    assert isinstance(history_manager, NoHistoryManager)
    gc.collect()
    gc.disable()
    try:
        gc.set_debug(gc.DEBUG_SAVEALL)
        # what IPython does with it when it resets, stores a cell and looks back
        history_manager.reset(new_session=False)
        history_manager.store_inputs(1, "x = 1")
        history_manager.store_output(1)
        assert list(history_manager.get_tail(10)) == []
        assert list(history_manager.get_range_by_str("1-2")) == []
        history_manager.end_session()
        del history_manager
        gc.collect()
        garbage = sorted(type(obj).__name__ for obj in gc.garbage)
    finally:
        gc.set_debug(0)
        gc.garbage.clear()
        gc.enable()
    assert garbage == []


def test_shell_creation_leaves_no_cyclic_garbage():
    import gc

    from solara.server.shell import SolaraInteractiveShell

    SolaraInteractiveShell()  # the first shell fills module level caches
    gc.collect()
    gc.disable()
    try:
        gc.set_debug(gc.DEBUG_SAVEALL)
        shell = SolaraInteractiveShell()
        gc.collect()
        garbage = sorted(type(obj).__name__ for obj in gc.garbage)
    finally:
        gc.set_debug(0)
        gc.garbage.clear()
        gc.enable()
    assert garbage == []
    magics_manager = shell.magics_manager
    assert magics_manager is not None
    assert magics_manager.registry["ScriptMagics"].script_magics == []
    assert "script" in magics_manager.magics["cell"]
