import dataclasses
from typing import Callable, Optional


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
