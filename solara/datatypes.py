import dataclasses
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")
U = TypeVar("U")


@dataclasses.dataclass(frozen=True)
class Action:
    name: str
    icon: Optional[str] = None
    on_click: Optional[Callable] = None


@dataclasses.dataclass(frozen=True)
class ColumnAction(Action):
    on_click: Optional[Callable[[str], None]] = None


@dataclasses.dataclass(frozen=True)
class CellAction(Action):
    on_click: Optional[Callable[[str, int], None]] = None


def _fallback_retry():
    raise RuntimeError("Should not happen")


@dataclasses.dataclass(frozen=True)
class Result(Generic[T]):
    value: Optional[T] = None
    error: Optional[Exception] = None
    running: bool = False
    progress: Optional[float] = None
    retry: Callable[[], Any] = lambda: None
    cancel: Callable[[], Any] = lambda: None
    cancelled: bool = False

    def __or__(self, next: Callable[["Result[T]"], "Result[U]"]):
        return next(self)


@dataclasses.dataclass(frozen=True)
class FileContentResult(Result[T]):
    @property
    def exists(self):
        return not isinstance(self.error, FileNotFoundError)
