import pytest
import contextlib
import solara.settings

import solara
from solara.validate_hooks import HookValidationError
import solara.validate_hooks


@contextlib.contextmanager
def hook_check_raise():
    prev = solara.settings.main.check_hooks
    solara.settings.main.check_hooks = "error"
    try:
        yield
    finally:
        solara.settings.main.check_hooks = prev


@contextlib.contextmanager
def hook_check_warn():
    prev = solara.settings.main.check_hooks
    solara.settings.main.check_hooks = "warn"
    try:
        yield
    finally:
        solara.settings.main.check_hooks = prev


def test_hooks_noqa_regex():
    regex = solara.validate_hooks.noqa_pattern
    assert regex.match("foo") is None
    assert regex.match("lala # noqa").groups() == (None, None)  # type: ignore
    assert regex.match("# noqa: SH102").groups() == ("SH102", None)  # type: ignore
    assert regex.match("# noqa: SH102, SH103").groups() == ("SH102", "SH103")  # type: ignore


def test_line_to_noqa():
    all = set(solara.validate_hooks.noqa_code_to_cause.values())
    assert solara.validate_hooks.line_to_noqa("def foo():") is None
    assert solara.validate_hooks.line_to_noqa("def foo():  # noqa") == all
    assert solara.validate_hooks.line_to_noqa("def foo():  # noqa: SH102") == {solara.validate_hooks.InvalidReactivityCause.CONDITIONAL_USE}
    assert solara.validate_hooks.line_to_noqa("def foo():  # noqa: SH102, SH103") == {
        solara.validate_hooks.InvalidReactivityCause.CONDITIONAL_USE,
        solara.validate_hooks.InvalidReactivityCause.LOOP_USE,
    }


def test_hook_use_invalid_loop():
    with hook_check_raise(), pytest.raises(HookValidationError):

        @solara.component
        def Page():
            for i in range(10):
                solara.use_state(1)
            solara.Text("Done")

    with hook_check_warn(), pytest.warns(UserWarning):

        @solara.component
        def Page2():
            for i in range(10):
                solara.use_state(1)
            solara.Text("Done")

    @solara.component
    def Page3():  # noqa: SH103
        for i in range(10):
            solara.use_state(1)
        solara.Text("Done")


def test_hook_use_invalid_conditional():
    with hook_check_warn(), pytest.warns(UserWarning):

        @solara.component
        def Page():
            if 1 > 3:
                solara.use_state(1)
            solara.Text("Done")

    @solara.component
    def Page2():
        if 1 > 3:
            solara.use_state(1)  # noqa: SH102
        solara.Text("Done")


def test_hook_use_early_return():
    with hook_check_raise(), pytest.raises(HookValidationError):

        @solara.component
        def Page():
            return
            solara.use_state(1)

    @solara.component
    def Page2():  # noqa: SH101
        return
        solara.use_state(1)

    @solara.component
    def Page3(  # noqa: SH101
        mul=1,
        ti=2,
        line=3,
        should="be triggered",
        by="having many and long",
        arguments="otherwise",
        out="linting will correct it",
    ):
        return
        solara.use_state(1)


def test_hook_use_nested_function():
    # sometimes we know that the use of a hook is stable, even when in a loop

    with hook_check_raise(), pytest.raises(HookValidationError):
        # single line
        @solara.component
        def Page():
            def inner_function():
                solara.use_state(1)

            inner_function()

    @solara.component
    def Page2():  # noqa: SH104
        def inner_function():
            solara.use_state(1)

        inner_function()


def test_hook_use_in_try():
    # sometimes we know that the use of a hook is stable, even when in a loop

    with hook_check_raise(), pytest.raises(HookValidationError):

        @solara.component
        def Page():
            try:
                solara.use_state(1)
            except ValueError:
                pass

    @solara.component
    def Page2():  # noqa: SH106
        try:
            solara.use_state(1)
        except ValueError:
            pass


def test_hook_use_invalid_assign():
    # sometimes we know that the use of a hook is stable, even when in a loop

    with hook_check_raise(), pytest.raises(HookValidationError):

        @solara.component
        def Page():
            alias = solara.use_state
            if 1 < 3:
                alias(1)
