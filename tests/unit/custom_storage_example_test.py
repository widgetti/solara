from unittest.mock import patch

import solara
import solara.lifecycle


def test_custom_storage_example_cleanup_runs_twice_for_one_kernel_id():
    # A restored kernel reuses its kernel id, so two kernel contexts with the same id can both
    # run the example's kernel start hook and then its cleanup. The second cleanup must not raise.
    from solara.website.pages.documentation.examples.general import custom_storage

    entries = [e for e in solara.lifecycle._on_kernel_start_callbacks if e.callback.__module__ == custom_storage.__name__]
    assert len(entries) == 1, entries
    entry = entries[0]
    with patch.object(solara, "get_kernel_id", return_value="kernel-1"):
        cleanups = [entry.callback(), entry.callback()]
        for cleanup in cleanups:
            assert cleanup is not None
            cleanup()
    assert "kernel-1" not in custom_storage.kernel_storage
