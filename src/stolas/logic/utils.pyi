"""Type stubs for utils module."""

from typing import Any, Callable, TypeVar
from stolas.types.option import Option

T = TypeVar("T")
U = TypeVar("U")

def wrap(cls: type[U]) -> Callable[[Any], U]:
    """Wrap value in class constructor."""
    ...

def when(
    predicate: Callable[[T], bool],
    then: Callable[[T], U],
    otherwise: Callable[[T], U],
) -> Callable[[T], U]:
    """Conditional execution."""
    ...

def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose functions left-to-right."""
    ...

def alt(default: T) -> Callable[[Option[T]], T]:
    """Unwrap Option or return default."""
    ...
