import dataclasses
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


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


@dataclasses.dataclass(frozen=True)
class Result(Generic[T]):
    value: Optional[T] = None
    error: Optional[Exception] = None
    running: bool = False


@dataclasses.dataclass(frozen=True)
class FileContentResult(Result[T]):
    @property
    def exists(self):
        return not isinstance(self.error, FileNotFoundError)
