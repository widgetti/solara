import warnings
from typing import Any, Callable, Dict, Union, overload, TypeVar
import typing_extensions
import reacton
from . import validate_hooks


P = typing_extensions.ParamSpec("P")
FuncT = TypeVar("FuncT", bound=Callable[..., reacton.core.Element])


@overload
def component(obj: None = None, mime_bundle: Dict[str, Any] = ...) -> Callable[[FuncT], FuncT]: ...


@overload
def component(obj: FuncT, mime_bundle: Dict[str, Any] = ...) -> FuncT: ...


@overload
def component(obj: Callable[P, None], mime_bundle: Dict[str, Any] = ...) -> Callable[P, reacton.core.Element]: ...


def component(
    obj: Union[Callable[P, None], FuncT, None] = None, mime_bundle: Dict[str, Any] = reacton.core.mime_bundle_default
) -> Union[Callable[[FuncT], FuncT], FuncT, Callable[P, reacton.core.Element]]:
    def wrapper(obj: Union[Callable[P, None], FuncT]) -> FuncT:
        try:
            validate_hooks.HookValidator(obj).run()
        except Exception as e:
            if not isinstance(e, validate_hooks.HookValidationError):
                # we probably failed because of an unknown reason, but we do not want to break the user's code
                warnings.warn(f"Failed to validate hooks for component {obj.__qualname__}: {e}")
            else:
                raise

        return reacton.component(obj, mime_bundle)  # type: ignore

    if obj is not None:
        return wrapper(obj)
    else:
        return wrapper
