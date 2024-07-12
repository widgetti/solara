from typing import Any, Callable, Dict, Union, overload
import typing_extensions
import reacton
from . import validate_hooks


P = typing_extensions.ParamSpec("P")
FuncT = typing_extensions.TypeVar("FuncT", bound=Callable[..., reacton.core.Element])


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
        validate_hooks.HookValidator(obj).run()
        return reacton.component(obj, mime_bundle)  # type: ignore

    if obj is not None:
        return wrapper(obj)
    else:
        return wrapper
