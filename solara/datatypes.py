import dataclasses
from enum import Enum
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


class ResultState(Enum):
    INITIAL = 1
    STARTING = 2
    WAITING = 3
    RUNNING = 4
    ERROR = 5
    FINISHED = 6
    CANCELLED = 7


@dataclasses.dataclass(frozen=True)
class Result(Generic[T]):
    value: Optional[T] = None
    error: Optional[Exception] = None
    state: ResultState = ResultState.INITIAL
    progress: Optional[float] = None

    def retry(self):
        # mypy does not like members that are callable
        # gets confused about self argument.
        # we wrap it to avoid hitting this error in user
        # code
        self._retry()  # type: ignore

    _retry: Callable[[], Any] = lambda: None
    cancel: Callable[[], Any] = lambda: None

    def __or__(self, next: Callable[["Result[T]"], "Result[U]"]):
        return next(self)


@dataclasses.dataclass(frozen=True)
class FileContentResult(Result[T]):
    @property
    def exists(self):
        return not isinstance(self.error, FileNotFoundError)
